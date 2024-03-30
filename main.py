import logging
from typing import List
from pydantic import BaseModel, Field, field_validator, ValidationError
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
from web3 import Web3, exceptions as web3_exceptions
import yaml
import time
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
    name: str
    rpc_endpoint: str

    @field_validator('name')
    def name_compatible_with_prometheus(cls, v):
        if ' ' in v or '"' in v or '{' in v or '}' in v:
            raise ValueError('name must be Prometheus label compatible')
        return v


class Address(BaseModel):
    address: str
    name: str
    network: str

    @field_validator('address')
    def address_is_valid_ethereum(cls, v):
        if not Web3.is_address(v):
            raise ValueError('address must be a valid Ethereum address')
        return v

    @field_validator('name')
    def name_compatible_with_prometheus(cls, v):
        if ' ' in v or '"' in v or '{' in v or '}' in v:
            raise ValueError('name must be Prometheus label compatible')
        return v


class Config(BaseModel):
    addresses: List[Address] = Field(..., min_length=1)
    networks: List[Network] = Field(..., min_length=1)
    update_interval_seconds: int = Field(..., ge=1)  # Ensure it's at least 60


def load_config(filepath: str) -> Config:
    try:
        with open(filepath, 'r') as file:
            config_data = yaml.safe_load(file)
        return Config.parse_obj(config_data)
    except (FileNotFoundError, yaml.YAMLError, ValidationError) as e:
        logger.fatal(f"Error loading or validating config file: {e}")
        raise SystemExit(e)


def update_metrics():
    timestamp = str(int(time.time()))  # Get current time as a string
    for network in config.networks:
        w3 = Web3(Web3.HTTPProvider(network.rpc_endpoint))
        for address in config.addresses:
            if address.network == network.name:
                try:
                    balance = w3.eth.get_balance(address.address)
                    balance_gauge.labels(
                        address=address.address,
                        address_name=address.name,
                        network_name=network.name,
                        updated_at=timestamp
                    ).set(balance)  # Include timestamp
                except web3_exceptions.Web3Exception as e:
                    logger.warning(
                        f"Failed to update balance for {address.address}: {e}"
                    )
            logger.info(
                f"Updated balance {address.name} as {address.address} on "
                f"{network.name} at {timestamp}"
            )


async def metrics(request):
    update_metrics()
    metrics_data = generate_latest()
    return Response(metrics_data, media_type="text/plain")


app = Starlette(debug=True, routes=[
    Route('/metrics', metrics)
])

try:
    config = load_config('config.yaml')
except SystemExit:
    exit()

balance_gauge = Gauge(
    'ethereum_balance', 'Ethereum Wallet Balance',
    ['address', 'address_name', 'network_name', 'updated_at'])


if __name__ == "__main__":
    import uvicorn
    import asyncio

    async def periodic_task():
        while True:
            update_metrics()
            await asyncio.sleep(config.update_interval_seconds)

    @app.on_event("startup")
    async def startup_event():
        task = asyncio.create_task(periodic_task())
        logger.info("Background task started")

    @app.on_event("shutdown")
    async def shutdown_event():
        task.cancel()
        await task
        logger.info("Background task stopped")

    uvicorn.run(app, host="0.0.0.0", port=8000)
