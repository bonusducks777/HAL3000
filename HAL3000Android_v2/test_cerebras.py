import os
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras

# Load .env from current directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), verbose=True)
api_key = os.environ.get("CEREBRAS_API_KEY")
print(f"[DEBUG] Using CEREBRAS_API_KEY: {api_key}")

client = Cerebras(api_key=api_key)

# Test with cortex-like messages
test_messages = [
    {
        "role": "system", 
        "content": "You are a mobile automation assistant. Analyze the screen and make decisions. Respond ONLY in valid JSON format."
    },
    {
        "role": "user", 
        "content": "Here are my device info:\nHost platform: WINDOWS\nMobile platform: android\nDevice ID: 5003TF1010001555\nDevice width: 1080\nDevice height: 2408"
    },
    {
        "role": "user", 
        "content": "Current goal: open the settings app. Please provide decisions in JSON format."
    }
]

try:
    print("[DEBUG] Testing Cerebras with structured output...")
    response = client.chat.completions.create(
        messages=test_messages,
        model="qwen-3-235b-a22b-instruct-2507",
        response_format={"type": "json_object"},
        max_completion_tokens=1000,
        temperature=0.7,
        top_p=0.8
    )
    print(f"[DEBUG] Response type: {type(response)}")
    print(f"[DEBUG] Response dir: {dir(response)}")
    print(f"[DEBUG] Full response: {response}")
    
    if hasattr(response, 'choices'):
        print(f"[DEBUG] Choices: {response.choices}")
        print(f"[DEBUG] Choice 0: {response.choices[0]}")
        print(f"[DEBUG] Choice 0 type: {type(response.choices[0])}")
        print(f"[DEBUG] Choice 0 dir: {dir(response.choices[0])}")
        if hasattr(response.choices[0], 'message'):
            print(f"[DEBUG] Message: {response.choices[0].message}")
            print(f"[DEBUG] Message type: {type(response.choices[0].message)}")
            print(f"[DEBUG] Message dir: {dir(response.choices[0].message)}")
            if hasattr(response.choices[0].message, 'content'):
                print(f"[DEBUG] Content: {response.choices[0].message.content}")
                
except Exception as e:
    print(f"[ERROR] Cerebras API call failed: {e}")
    import traceback
    traceback.print_exc()
