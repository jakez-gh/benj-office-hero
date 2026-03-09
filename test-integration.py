import aiohttp
import asyncio
import json

async def test_login():
    async with aiohttp.ClientSession() as session:
        # Test 1: Invalid credentials
        print("Test 1: Invalid credentials")
        try:
            async with session.post(
                'http://localhost:8000/auth/login',
                json={'email': 'invalid@test.com', 'password': 'wrong'}
            ) as resp:
                result = await resp.json()
                print(f"  Status: {resp.status}")
                print(f"  Response: {result}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # Test 2: Valid credentials
        print("\nTest 2: Valid credentials")
        try:
            async with session.post(
                'http://localhost:8000/auth/login',
                json={'email': 'test@example.com', 'password': 'password123'}
            ) as resp:
                result = await resp.json()
                print(f"  Status: {resp.status}")
                if resp.status == 200:
                    print(f"  ✓ Login successful!")
                    print(f"  Access token: {result.get('access_token', 'N/A')[:50]}...")
                    print(f"  User: {result.get('user')}")
                    
                    # Test 3: Use token in protected request
                    access_token = result['access_token']
                    print("\nTest 3: Protected request with token")
                    async with session.get(
                        'http://localhost:8000/health',
                        headers={'Authorization': f'Bearer {access_token}'}
                    ) as resp2:
                        print(f"  Status: {resp2.status}")
                        result2 = await resp2.json()
                        print(f"  Response: {result2}")
                else:
                    print(f"  Response: {result}")
        except Exception as e:
            print(f"  Error: {e}")

asyncio.run(test_login())
