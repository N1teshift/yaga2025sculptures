# Node-RED Flow Management

This directory contains the Node-RED flows for the sculpture control dashboard.

## Structure

The main `flow.json` file, which is used by Node-RED, is **auto-generated** and should not be edited directly.

The flows are split into smaller, more manageable files located in the `flows/` subdirectory. Each file corresponds to a specific part of the dashboard's functionality:

-   `flow_config.json`: Contains global configuration nodes (MQTT broker, UI tabs, groups).
-   `flow_system.json`: Contains system-wide controls (Plan selection, Emergency Stop).
-   `flow_sculpture1.json`: All nodes related to Sculpture 1.
-   `flow_sculpture2.json`: All nodes related to Sculpture 2.
-   `flow_sculpture3.json`: All nodes related to Sculpture 3.

## Making Changes

To make changes to the Node-RED flow:

1.  Identify and edit the appropriate file(s) in the `flows/` directory.
2.  Run the `combine_flows.js` script to regenerate the main `flow.json` file.

```bash
node server/nodered/combine_flows.js
```

This script will read all `.json` files in the `flows/` directory and combine them into `server/nodered/flow.json`. After running the script, you will need to restart Node-RED to see the changes. 