#pragma once

#ifdef __cplusplus
extern "C" { // Ensure C linkage for exported functions
#endif

// Exported function to print address
__declspec(dllexport) void PrintAddress();

// Stub functions for common d3d8.dll exports (to prevent game crashes)
__declspec(dllexport) void Direct3D8EnableMaximizedModeShim();
__declspec(dllexport) void *Direct3DCreate8(UINT SDKVersion);
// Add more stub exports as needed if the game complains about missing functions

#ifdef __cplusplus
}
#endif