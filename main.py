import json
import asyncio
import aiohttp
import websockets
import ssl


async def get_enterprise_edges(veco, token, enterprise_id):
    ### Get list of edges and UUIDs ###
    print("Fetching list of enterprise edges...")
    connector = aiohttp.TCPConnector(ssl=False) 

    async with aiohttp.ClientSession(
        headers={"Authorization": f"Token {token}"}, connector=connector
    ) as session:
        async with session.post(
            f"https://{veco}/portal/",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "enterprise/getEnterpriseEdges",
                "params": {"enterpriseId": enterprise_id, "limit": 500},
            },
        ) as req:
            response = await req.json()
            if "result" in response and "data" in response["result"]:
                print(f"Fetched {len(response['result']['data'])} edges.")
                return response["result"]["data"]
            else:
                print("Error fetching edges:", response)
                return []


async def run_diagnostics(veco, token, edges, diag_name, parameters = None):
    ### Run diagnostics command ###
    parameters = parameters or {} 
    print("Connecting to WebSocket for diagnostics...")

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with websockets.connect(
        f"wss://{veco}/ws/",
        extra_headers={"Authorization": f"Token {token}"},
        ssl=ssl_context,  
    ) as ws:
        print("WebSocket connection established. Waiting for token...")
        token_msg = json.loads(await ws.recv())
        if "token" not in token_msg:
            print("Error: WebSocket did not return a token.")
            return

        ws_token = token_msg["token"]
        print("Received WebSocket token. Starting diagnostics...")

        results = []
        for edge in edges:
            logical_id = edge.get("logicalId")
            if not logical_id:
                continue

            print(f"Running diagnostics for edge: {edge.get('name', 'Unknown')} (Logical ID: {logical_id})...")
            await ws.send(
                json.dumps(
                    {
                        "action": "runDiagnostics",
                        "data": {"logicalId": logical_id, "resformat": "JSON", "test": diag_name, "parameters": parameters},
                        "token": ws_token,
                    }
                )
            )

            response = json.loads(await ws.recv())
            if response.get("action") == "runDiagnostics":
                result = response.get("data", {}).get("results", {}).get("output", "No output received.")
                print(f"Diagnostics result for edge {logical_id}: {result}")
                results.append({"logical_id": logical_id, "result": result})
            else:
                print(f"Unexpected response for edge {logical_id}: {response}")

        print("Diagnostics completed.")
        return results


async def main():
    veco = "192.168.20.11"  
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlblV1aWQiOiJiZmVjZGM2Ni1kYjM1LTQyNWItYmNkYi1iZTM5OWQzOTg3YjIiLCJleHAiOjE3NjM5MDA5OTAsInV1aWQiOiI4NWFkZjU5Yi0yNDgyLTQ4YmYtYTZjZi02YTFmYzFjMTdmNTYiLCJpYXQiOjE3MzIzNjQ5OTl9.gaWHDw4JVBgo2M_3T4kccvIfLxERggYmHvtCKuXBsEg" 
    enterprise_id = 1  

    edges = await get_enterprise_edges(veco, token, enterprise_id)
    
    await run_diagnostics(
        veco,
        token,
        edges,
        diag_name="QUAGGA_OSPF_TBL",
        #parameters={"count": 1000} # If params required, uncomment this, otherwise empty dict passes
    )

if __name__ == "__main__":
    asyncio.run(main())
