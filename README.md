FServer is a Fuego json and yaml test object web server.


Introduction
============
FServer handles the user interface (HTML),
as well as web-based object storage for 
the following Fuego objects
 * Tests
 * Requests
 * Runs

In the future, additional objects may be stored, including:
 * test reviews
 * test target packages
 * test report definitions
 * lab definitions
 * board definitions
 * user objects

Starting in foreground mode
===========================
To start fserver in foreground mode, cd to the top-level directory,
and run the script: start_server.

You may specify a TCP/IP port address for the server to use, on the
command line, like so:
 $ start_server 8001

By default, port 8000 is used.

In foreground mode, the program runs directly in the terminal where
fserver was started, and log messages are displayed on the screen
as the server processes network requests.

To stop the server, use CTRL-C (possibly a few times), to interrupt
the running server.

To start fserver in background mode, use the script: start_local_bg_server.
You may specify the TCP/IP port address fro the server to use, on the
command line, like so:
 $ start_local_bg_server [<port>]

In this case, the log data from the server will be placed in the
file: /tmp/fserver-server-log.output

To stop the server, use the following command:
  $ kill $(pgrep -f fserver-server)

Accessing the server
====================
To access the server using a web browser, go to:
 http://<ip address>:<port>/fserver.py

To access the server using the command line, use:
 * ftc put-request
 * ftc list-requests
 * ftc run-request
 * ftc put-run

Configuring Fuego to access the server
======================================
To access the server using Fuego's ftc command, you need to configure
fuego with the address of the server.
Put the following lines in the fuego/fuego-ro/conf/fuego.conf

server_type=fuego
server_domain=localhost:8091/

If using the global fserver service, use the following configuration:
server_type=fuego
server_domain=fuegotest.org/cgi-bin

