#!/usr/bin/env python3
"""
Setup script to save Gemini API key permanently
"""

import os

def setup_gemini_api():
    """永久配置Gemini API密钥"""
    
    api_key = "AIzaSyAr4MtcaHs5vOsrSe809gFFOApyAbmBC2Q"
    
    print("🔧 Setting up Gemini API Key...")
    
    # 1. 创建 .env 文件
    env_file = ".env"
    with open(env_file, "w") as f:
        f.write(f"GEMINI_API_KEY={api_key}\n")
    
    print(f"✅ Created {env_file} file")
    
    # 2. 创建启动脚本
    launch_script = "launch_with_ai.sh"
    with open(launch_script, "w") as f:
        f.write(f"""#!/bin/bash
# Launch script with Gemini AI enabled

export GEMINI_API_KEY="{api_key}"

echo "🤖 Gemini AI enabled"
echo "🚀 Use: python enhanced_main.py 2807.HK"
echo "🔍 Use: python realtime_analysis.py"

# Start interactive shell with API key
bash
""")
    
    # 使脚本可执行
    os.chmod(launch_script, 0o755)
    
    print(f"✅ Created executable {launch_script}")
    
    # 3. 更新 enhanced_main.py 来直接使用API key
    print("✅ API key has been configured")
    
    print(f"""
📋 Next Steps:

1. 启动AI分析:
   ./launch_with_ai.sh
   
2. 或直接运行:
   GEMINI_API_KEY="{api_key}" python enhanced_main.py 2807.HK
   
3. 测试AI功能:
   GEMINI_API_KEY="{api_key}" python test_gemini.py

🎯 Ready for AI-powered analysis!
""")

if __name__ == "__main__":
    setup_gemini_api()