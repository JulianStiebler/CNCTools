#include "pch.h"
#include <windows.h>
#include <stdio.h>
#include <DbgHelp.h>
#include <Psapi.h>
#pragma comment(lib, "dbghelp.lib")
#pragma comment(lib, "psapi.lib")

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved)
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
    {
        // Konsole öffnen
        AllocConsole();
        FILE* pCout;
        freopen_s(&pCout, "CONOUT$", "w", stdout);
        printf("DLL geladen!\n");

        FILE* fp;
        fopen_s(&fp, "function_address_log.txt", "w");
        if (fp) {
            fprintf(fp, "--- Exportierte Funktionsadressen ---\n");
            printf("--- Exportierte Funktionsadressen ---\n"); // Auch ins CMD

            HMODULE gameModule = GetModuleHandle(NULL);
            if (gameModule) {
                fprintf(fp, "\n[Spielmodul Basisadresse: %p]\n", gameModule);
                printf("\n[Spielmodul Basisadresse: %p]\n", gameModule);

                MODULEINFO moduleInfo;
                if (GetModuleInformation(GetCurrentProcess(), gameModule, &moduleInfo, sizeof(MODULEINFO))) {
                    DWORD_PTR baseAddress = (DWORD_PTR)moduleInfo.lpBaseOfDll;
                    DWORD moduleSize = moduleInfo.SizeOfImage;
                    PIMAGE_DOS_HEADER dosHeader = (PIMAGE_DOS_HEADER)baseAddress;

                    if (dosHeader->e_magic == IMAGE_DOS_SIGNATURE) {
                        PIMAGE_NT_HEADERS ntHeaders = (PIMAGE_NT_HEADERS)((BYTE*)baseAddress + dosHeader->e_lfanew);
                        if (ntHeaders->Signature == IMAGE_NT_SIGNATURE) {
                            DWORD exportDirSize = 0;
                            IMAGE_EXPORT_DIRECTORY* exportDirectory = (IMAGE_EXPORT_DIRECTORY*)
                                ImageDirectoryEntryToData((HMODULE)baseAddress, TRUE, IMAGE_DIRECTORY_ENTRY_EXPORT, &exportDirSize);

                            if (exportDirectory) {
                                DWORD* functionAddresses = (DWORD*)((BYTE*)baseAddress + exportDirectory->AddressOfFunctions);
                                DWORD* functionNames = (DWORD*)((BYTE*)baseAddress + exportDirectory->AddressOfNames);
                                WORD* functionOrdinals = (WORD*)((BYTE*)baseAddress + exportDirectory->AddressOfNameOrdinals);

                                for (DWORD i = 0; i < exportDirectory->NumberOfNames; ++i) {
                                    char* functionName = (char*)((BYTE*)baseAddress + functionNames[i]);
                                    DWORD functionAddressRVA = functionAddresses[functionOrdinals[i]];
                                    DWORD_PTR functionAddress = baseAddress + functionAddressRVA;

                                    fprintf(fp, "Funktionsname: %s, Adresse: %p\n", functionName, (void*)functionAddress);
                                    printf("Funktionsname: %s, Adresse: %p\n", functionName, (void*)functionAddress);
                                }
                            }
                            else {
                                fprintf(fp, "Error: No Export Directory found.\n");
                                printf("Error: No Export Directory found.\n");
                            }
                        }
                        else {
                            fprintf(fp, "Error: Invalid NT Headers.\n");
                            printf("Error: Invalid NT Headers.\n");
                        }
                    }
                    else {
                        fprintf(fp, "Error: Invalid DOS Header.\n");
                        printf("Error: Invalid DOS Header.\n");
                    }
                }
                else {
                    fprintf(fp, "Error: GetModuleInformation fehlgeschlagen.\n");
                    printf("Error: GetModuleInformation fehlgeschlagen.\n");
                }
            }
            else {
                fprintf(fp, "Error: GetModuleHandle konnte Spielmodul nicht abrufen.\n");
                printf("Error: GetModuleHandle konnte Spielmodul nicht abrufen.\n");
            }

            // Optional: Adresse von d3d8.dll auch ausgeben
            HMODULE dllModule = GetModuleHandle(L"d3d8.dll");
            if (dllModule) {
                fprintf(fp, "\n[d3d8.dll Modul Basisadresse: %p]\n", dllModule);
                printf("\n[d3d8.dll Modul Basisadresse: %p]\n", dllModule);
            }
            else {
                fprintf(fp, "\nFehler: GetModuleHandle konnte d3d8.dll Modul nicht abrufen.\n");
                printf("\nFehler: GetModuleHandle konnte d3d8.dll Modul nicht abrufen.\n");
            }
            fclose(fp);
        }
        break;
    }
    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
    case DLL_PROCESS_DETACH:
        break;
    }
    return TRUE;
}

void __declspec(dllexport) PrintAddress() {
    FILE* fp;
    fopen_s(&fp, "function_address_log.txt", "a+");
    if (fp) {
        fprintf(fp, "PrintAddress() aufgerufen - (Platzhalterfunktion)\n");
        fclose(fp);
    }
}

__declspec(dllexport) void Direct3D8EnableMaximizedModeShim() { }
__declspec(dllexport) void* Direct3DCreate8(UINT SDKVersion) { return nullptr; }
