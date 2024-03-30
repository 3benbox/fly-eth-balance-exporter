
Write a python program that reads a config.yaml file with the following format

```
addresses:
  - address: <ethereum address>
    name: <friendly name for the address>
    network: <network key>
networks:
  - name: <key for reference in an address>
    rpc-endpoint: <rpc-endpoint for the network>
```

The program then starts a prometheus compatible endpoint for scraping the wallet balances of the addresses.

The endpoint returns prometheus metrics for the address balance using the network rpc-endpoint.

The metrics should have labels with the address and both the address and network names.

Please check the yaml values for correctness.

The address should be a valid ethereum address and the names should be prometheus label compatible.

Use pydantic when applicable.