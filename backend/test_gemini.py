from backend.config import client

try:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say hello in one sentence.",
    )

    print("SUCCESS")
    print(response)
    print("\nTEXT:")
    print(response.text)

except Exception as e:
    print("ERROR:")
    print(e)
