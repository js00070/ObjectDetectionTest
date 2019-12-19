import websocket
import json
import time

ws = websocket.WebSocket()
ws.connect("ws://192.168.1.106:8181",subprotocols=["ssr-json"])

def NewSource(source_info):
    msg = json.dumps(["new-src",[source_info]])
    ws.send(msg)
    # res = ws.recv()
    # print(res)

def ModSource(source_id, source_info):
    msg = json.dumps(["mod-src",{
        source_id: source_info
    }])
    ws.send(msg)
    # res = ws.recv()
    # print(res)

def DeleteSource(source_id):
    msg = json.dumps(["del-src",[source_id]])
    ws.send(msg)
    # res = ws.recv()
    # print(res)


def test():
    time.sleep(5)

    NewSource({
        "id": "src1",
        "name": "person1",
        "port-number": 1,
        "pos": [1,1,0],
        "volume": 0.1
    })

    time.sleep(1)

    ModSource("src1",{
        "pos": [0,1,0]
    })

    time.sleep(1)

    ModSource("src1",{
        "pos": [-1,1,0]
    })

    time.sleep(1)

    DeleteSource("src1")

if __name__ == "__main__":
    test()