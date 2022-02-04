"""
Test out a network in the following configuration:

 [ client ] :        REQ
 [ server ] : SUB    DEALER  <-> async handler
 [ admin ]  : PUB

The client sends requests to the server every 0.1 seconds.
The server handles these requests by launching background jobs.

After 0.5 seconds, the admin changes the server's options.
Then, after 1 second, the admin stops the server.
"""

import asyncio
import time

import pytest

from aiowire import EventLoop, Poller, Call

import zmq
from zmq.asyncio import Context

control = 'inproc://test_control'
url     = 'inproc://test_zmq'

def new_socket(ctx, stype, cli=False):
    s = ctx.socket( stype )
    s.setsockopt( zmq.LINGER, 0 )
    if cli:
        s.setsockopt( zmq.IMMEDIATE, 1 )
    return s

class Server:
    def __init__(self, ctx, url, ctrl):
        self.control = new_socket(ctx, zmq.SUB)
        self.control.connect(ctrl)
        self.control.subscribe(b'')

        self.sock = new_socket(ctx, zmq.ROUTER)
        self.sock.bind( url )
        self.status = b'ok'
    
    async def admin(self, ev):
        msg = await self.control.recv()
        if msg == b'terminate':
            self.poller.shutdown()
        else:
            self.status = msg

    async def handle_req(self, ev):
        msg = await self.sock.recv_multipart()
        id_client = msg[0]
        print( "Sever recvd: Sender ID: {};\tmessage: {}".format(
                        id_client, msg)
        )

        return Call(self.send_ans, id_client, self.status)

    async def send_ans(self, id_client, msg):
        await asyncio.sleep(0.05)
        await self.sock.send_multipart([id_client, b'', msg])

    async def __call__(self, ev):
        self.poller = Poller({
                            self.control : self.admin,
                            self.sock : self.handle_req
                        })
        return self.poller

async def server(ev):
    # start the server and mimick the control processes
    ctx = Context.instance()
    sock = new_socket(ctx, zmq.PUB)
    sock.bind(control)

    ev.start( Server(ctx, url, control) )
    ev.start( Call(asyncio.sleep, 0.5) >> Call(sock.send_string, "shutdown") )
    return Call(asyncio.sleep, 1.0) \
           >> Call(sock.send_string, "terminate") \
           >> Call(sock.close)

class Client:
    def __init__(self, url):
        ctx = Context.instance()
        sock = new_socket(ctx, zmq.REQ)
        sock.connect(url)
        self.sock = sock

        self.nok = 0
        self.nshut = 0

    async def __call__(self, ev):
        for i in range(15):
            await self.sock.send_multipart([b'', b'hello'])
            ans = await self.sock.recv()
            print(f"received: {ans}")
            if ans == b'ok':
                self.nok += 1
            if ans == b'shutdown':
                self.nshut += 1
            await asyncio.sleep(0.03)

        self.sock.close()

@pytest.mark.asyncio
async def test_run():
    C = Client(url)
    async with EventLoop(2.0) as ev:
        ev.start( server )
        ev.start( C )
    assert C.nok > 1
    assert C.nshut > 1

if __name__=="__main__":
    asyncio.run( run() )
