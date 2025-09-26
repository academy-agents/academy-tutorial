import os
from globus_compute_sdk import GCExecutor

def remote_function():
    import socket
    return socket.gethostname()

def main():
    if "ACADEMY_TUTORIAL_ENDPOINT" not in os.environ:
        raise ValueError("ACADEMY_TUTORIAL_ENDPOINT must be set for execute function.")
    
    with GCExecutor(os.environ['ACADEMY_TUTORIAL_ENDPOINT']) as executor:
        future = executor.submit(remote_function)
        print(f'Function was run on: {future.result()}')

if __name__ == "__main__":
    main()
