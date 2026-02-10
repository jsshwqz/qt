import sys
import os

print("Verifying v2.1 modules...")

try:
    import exceptions
    print("✅ exceptions imported")
except ImportError as e:
    print(f"❌ exceptions import failed: {e}")

try:
    import log_manager
    print("✅ log_manager imported")
except ImportError as e:
    print(f"❌ log_manager import failed: {e}")

try:
    import config_manager
    print("✅ config_manager imported")
except ImportError as e:
    print(f"❌ config_manager import failed: {e}")

try:
    import adb_manager
    print("✅ adb_manager imported")
except ImportError as e:
    print(f"❌ adb_manager import failed: {e}")

try:
    # Use importlib for v2.1 file due to dot
    import importlib.util
    spec = importlib.util.spec_from_file_location("video_decoder_v2_1", "video_decoder_v2.1.py")
    vd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vd)
    print("✅ video_decoder_v2.1 imported")
    
    if hasattr(vd, 'VideoDecoder'):
        print("   ✅ VideoDecoder class found")
    else:
        print("   ❌ VideoDecoder class MISSING")
        
except Exception as e:
    print(f"❌ video_decoder_v2.1 import failed: {e}")

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("scrcpy_client_v2_1", "scrcpy_client_v2.1.py")
    cl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cl)
    print("✅ scrcpy_client_v2.1 imported")
except Exception as e:
    print(f"❌ scrcpy_client_v2.1 import failed: {e}")
