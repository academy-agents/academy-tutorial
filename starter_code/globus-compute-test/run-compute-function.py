from globus_compute_sdk import Executor

TUTORIAL_ENDPOINT_UUID = '707fe7ed-6f06-4ec3-877f-1c1f0e9aeb84'

def remote_function():
    import socket
    print(socket.gethostname())

def main():
    with Executor(TUTORIAL_ENDPOINT_UUID) as executor:
        future = executor.submit(remote_function)
        print(f'Function was run on: {future.result()}')

if __name__ == "__main__":
    main()