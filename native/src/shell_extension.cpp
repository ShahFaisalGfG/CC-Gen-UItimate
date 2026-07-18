// shell_extension.cpp - IExplorerCommand COM in-process server
// Provides "Generate Subtitles with CC-Gen-Ultimate" in the
// Windows 11 first-level context menu via ExplorerCommandHandler.

#define WIN32_LEAN_AND_MEAN
#define STRICT
#include <windows.h>
#include <shlobj.h>
#include <shobjidl.h>
#include <objbase.h>
#include <string>
#include <vector>

// ---------------------------------------------------------------------------
// Module state
// ---------------------------------------------------------------------------

static HMODULE g_hModule  = nullptr;
static LONG    g_refCount = 0;

// ---------------------------------------------------------------------------
// CLSID
// {5E1DC6F3-4ECF-47F4-BB26-F8D3097DE182}  - Generate Subtitles
// ---------------------------------------------------------------------------

static const GUID CLSID_CcGenSubtitles = {
    0x5E1DC6F3, 0x4ECF, 0x47F4,
    {0xBB, 0x26, 0xF8, 0xD3, 0x09, 0x7D, 0xE1, 0x82}
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

static std::wstring dllDirectory()
{
    wchar_t buf[MAX_PATH] = {};
    GetModuleFileNameW(g_hModule, buf, MAX_PATH);
    std::wstring s(buf);
    auto pos = s.rfind(L'\\');
    if (pos != std::wstring::npos) s.resize(pos);
    return s;
}

static std::wstring quoted(const std::wstring& s)
{
    return L"\"" + s + L"\"";
}

// ---------------------------------------------------------------------------
// CcGenCommand - IExplorerCommand + IUnknown
// ---------------------------------------------------------------------------

class CcGenCommand : public IExplorerCommand
{
    LONG _refs;

public:
    CcGenCommand() : _refs(1)
    {
        InterlockedIncrement(&g_refCount);
    }

    ~CcGenCommand()
    {
        InterlockedDecrement(&g_refCount);
    }

    // ── IUnknown ──────────────────────────────────────────────────────────

    STDMETHODIMP QueryInterface(REFIID riid, void** ppv) override
    {
        if (!ppv) return E_POINTER;
        if (IsEqualIID(riid, IID_IUnknown) || IsEqualIID(riid, IID_IExplorerCommand)) {
            *ppv = static_cast<IExplorerCommand*>(this);
            AddRef();
            return S_OK;
        }
        *ppv = nullptr;
        return E_NOINTERFACE;
    }

    STDMETHODIMP_(ULONG) AddRef() override
    {
        return InterlockedIncrement(&_refs);
    }

    STDMETHODIMP_(ULONG) Release() override
    {
        LONG r = InterlockedDecrement(&_refs);
        if (r == 0) delete this;
        return r;
    }

    // ── IExplorerCommand ──────────────────────────────────────────────────

    STDMETHODIMP GetTitle(IShellItemArray*, LPWSTR* ppszName) override
    {
        if (!ppszName) return E_POINTER;
        const wchar_t* title = L"Generate Subtitles with CC-Gen-Ultimate";
        size_t len = wcslen(title) + 1;
        *ppszName = static_cast<LPWSTR>(CoTaskMemAlloc(len * sizeof(wchar_t)));
        if (!*ppszName) return E_OUTOFMEMORY;
        wcscpy_s(*ppszName, len, title);
        return S_OK;
    }

    STDMETHODIMP GetIcon(IShellItemArray*, LPWSTR* ppszIcon) override
    {
        if (!ppszIcon) return E_POINTER;
        std::wstring icon = dllDirectory() + L"\\icons\\CCGenUltimate.ico";
        size_t len = icon.size() + 1;
        *ppszIcon = static_cast<LPWSTR>(CoTaskMemAlloc(len * sizeof(wchar_t)));
        if (!*ppszIcon) return E_OUTOFMEMORY;
        wcscpy_s(*ppszIcon, len, icon.c_str());
        return S_OK;
    }

    STDMETHODIMP GetToolTip(IShellItemArray*, LPWSTR* ppszInfotip) override
    {
        if (!ppszInfotip) return E_POINTER;
        *ppszInfotip = nullptr;
        return E_NOTIMPL;
    }

    STDMETHODIMP GetCanonicalName(GUID* pguid) override
    {
        if (!pguid) return E_POINTER;
        *pguid = CLSID_CcGenSubtitles;
        return S_OK;
    }

    STDMETHODIMP GetState(IShellItemArray*, BOOL, EXPCMDSTATE* pState) override
    {
        if (!pState) return E_POINTER;
        *pState = ECS_ENABLED;
        return S_OK;
    }

    STDMETHODIMP GetFlags(EXPCMDFLAGS* pFlags) override
    {
        if (!pFlags) return E_POINTER;
        *pFlags = ECF_DEFAULT;
        return S_OK;
    }

    STDMETHODIMP EnumSubCommands(IEnumExplorerCommand** ppEnum) override
    {
        if (!ppEnum) return E_POINTER;
        *ppEnum = nullptr;
        return E_NOTIMPL;
    }

    STDMETHODIMP Invoke(IShellItemArray* psia, IBindCtx*) override
    {
        std::wstring exePath = dllDirectory() + L"\\CC-Gen-Ultimate.exe";

        std::vector<std::wstring> paths;
        if (psia) {
            DWORD count = 0;
            psia->GetCount(&count);
            paths.reserve(count);
            for (DWORD i = 0; i < count; i++) {
                IShellItem* psi = nullptr;
                if (SUCCEEDED(psia->GetItemAt(i, &psi))) {
                    LPWSTR disp = nullptr;
                    if (SUCCEEDED(psi->GetDisplayName(SIGDN_FILESYSPATH, &disp))) {
                        paths.emplace_back(disp);
                        CoTaskMemFree(disp);
                    }
                    psi->Release();
                }
            }
        }

        std::wstring cmdLine = quoted(exePath);
        for (const auto& p : paths) {
            cmdLine += L" ";
            cmdLine += quoted(p);
        }

        STARTUPINFOW si        = {};
        si.cb                  = sizeof(si);
        PROCESS_INFORMATION pi = {};
        CreateProcessW(nullptr,
                       cmdLine.data(),
                       nullptr, nullptr,
                       FALSE,
                       CREATE_NO_WINDOW,
                       nullptr, nullptr,
                       &si, &pi);
        if (pi.hProcess) CloseHandle(pi.hProcess);
        if (pi.hThread)  CloseHandle(pi.hThread);
        return S_OK;
    }
};

// ---------------------------------------------------------------------------
// CcGenClassFactory - IClassFactory
// ---------------------------------------------------------------------------

class CcGenClassFactory : public IClassFactory
{
    LONG _refs;

public:
    CcGenClassFactory() : _refs(1)
    {
        InterlockedIncrement(&g_refCount);
    }

    ~CcGenClassFactory()
    {
        InterlockedDecrement(&g_refCount);
    }

    // IUnknown
    STDMETHODIMP QueryInterface(REFIID riid, void** ppv) override
    {
        if (!ppv) return E_POINTER;
        if (IsEqualIID(riid, IID_IUnknown) || IsEqualIID(riid, IID_IClassFactory)) {
            *ppv = static_cast<IClassFactory*>(this);
            AddRef();
            return S_OK;
        }
        *ppv = nullptr;
        return E_NOINTERFACE;
    }

    STDMETHODIMP_(ULONG) AddRef() override { return InterlockedIncrement(&_refs); }

    STDMETHODIMP_(ULONG) Release() override
    {
        LONG r = InterlockedDecrement(&_refs);
        if (r == 0) delete this;
        return r;
    }

    // IClassFactory
    STDMETHODIMP CreateInstance(IUnknown* outer, REFIID riid, void** ppv) override
    {
        if (!ppv) return E_POINTER;
        if (outer) return CLASS_E_NOAGGREGATION;
        auto* cmd = new (std::nothrow) CcGenCommand();
        if (!cmd) return E_OUTOFMEMORY;
        HRESULT hr = cmd->QueryInterface(riid, ppv);
        cmd->Release();
        return hr;
    }

    STDMETHODIMP LockServer(BOOL lock) override
    {
        lock ? InterlockedIncrement(&g_refCount) : InterlockedDecrement(&g_refCount);
        return S_OK;
    }
};

// ---------------------------------------------------------------------------
// DLL entry points
// ---------------------------------------------------------------------------

BOOL APIENTRY DllMain(HMODULE hModule, DWORD fdwReason, LPVOID)
{
    if (fdwReason == DLL_PROCESS_ATTACH) {
        g_hModule = hModule;
        DisableThreadLibraryCalls(hModule);
    }
    return TRUE;
}

STDAPI DllGetClassObject(REFCLSID clsid, REFIID riid, void** ppv)
{
    if (!ppv) return E_POINTER;
    if (!IsEqualCLSID(clsid, CLSID_CcGenSubtitles))
        return CLASS_E_CLASSNOTAVAILABLE;

    IClassFactory* factory = new (std::nothrow) CcGenClassFactory();
    if (!factory) return E_OUTOFMEMORY;
    HRESULT hr = factory->QueryInterface(riid, ppv);
    factory->Release();
    return hr;
}

STDAPI DllCanUnloadNow()
{
    return g_refCount == 0 ? S_OK : S_FALSE;
}
