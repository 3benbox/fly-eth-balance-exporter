# fly-eth-balance-exporter

Prometheus exporter of Ethereum account balances using the Fly.io platform.

## Configure

Update the `config.yaml` file with the Ethereum addresses you want to monitor.

Sensitive value can be resolved through environment variables with the `${VAR}` syntax.

## Deploy

Not sure exactly how to organize this.

- Deploy the app, it will fail if you have any secrets in the `config.yaml` file.
- Set secrets, it auto deploys and starts working.

```bash
flyctl deploy
```

Check the logs like this:

```bash
flyctl logs
```

Set a secret for your `config.yaml` file:

```bash
flyctl secrets set NAME=VALUE
```

## Metrics

Metric name: ethereum_balance
labels: address, address_name, network_name

Example:

```
ethereum_balance{address="0x449bA5c62A77da29031F56724fA1bF8aeC75Fa76",address_name="doubtingben.eth",network_name="mainnet"} 1.3349950070172682e+16
```