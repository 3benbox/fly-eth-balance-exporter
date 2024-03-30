import logging
from typing import List
from pydantic import BaseModel, Field, validator, ValidationError
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
from web3 import Web3, exceptions as web3_exceptions
import yaml
from prometheus_client import generate_latest, Gauge

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_valid_ethereum_address(cls, v):
    if not Web3.is_address(v):
        raise ValueError('Must be a valid Ethereum address')
    return v


def is_prometheus_label_compatible(cls, v):
    if any(c in v for c in ' "{}'):
        raise ValueError('Must be Prometheus label compatible')
    return v


class Network(BaseModel):
    name: str = Field(..., min_length=1)
    rpc_endpoint: str = Field(..., min_length=1)

    _name_validator = validator('name', allow_reuse=True)(
        is_prometheus_label_compatible)


class Address(BaseModel):
    address: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    network: str = Field(..., min_length=1)

    _address_validator = validator('address', allow_reuse=True)(
        is_valid_ethereum_address)
    _name_validator = validator('name', allow_reuse=True)(
        is_prometheus_label_compatible)


class Config(BaseModel):
    addresses: List[Address] = Field(..., min_items=1)
    networks: List[Network] = Field(..., min_items=1)


def load_config(filepath: str) -> Config:
    try:
        with open(filepath, 'r') as file:
            config_data = yaml.safe_load(file)
        return Config.parse_obj(config_data)
    except (FileNotFoundError, yaml.YAMLError, ValidationError) as e:
        logger.fatal(f"Error loading or validating config file: {e}")
        raise SystemExit(e)


try:
    config = load_config('config.yaml')
except SystemExit:
    exit()


balance_gauge = Gauge(
    'ethereum_balance', 'Ethereum Wallet Balance',
    ['address', 'address_name', 'network_name'])


def update_metrics():
    for network in config.networks:
        w3 = Web3(Web3.HTTPProvider(network.rpc_endpoint))
        for address in config.addresses:
            if address.network == network.name:
                try:
                    balance = w3.eth.get_balance(address.address)
                    # balance_eth = Web3.fromWei(balance, 'ether')
                    balance_gauge.labels(
                        address=address.address,
                        address_name=address.name,
                        network_name=network.name).set(balance)
                except web3_exceptions.Web3Exception as e:
                    logger.warning(
                        f"Failed to update balance for {address.address}: {e}")


async def metrics(request):
    update_metrics()
    metrics_data = generate_latest()
    return Response(metrics_data, media_type="text/plain")


app = Starlette(debug=True, routes=[
    Route('/metrics', metrics)
])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
