
try:
    with open('.env', 'rb') as f:
        content = f.read()
    print(f"Raw content: {content}")
    print(f"Decoded: {content.decode('utf-8', errors='replace')}")
except Exception as e:
    print(e)
