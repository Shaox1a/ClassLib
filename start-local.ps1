[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8000,
    [switch]$SkipInstall,
    [switch]$SetupOnly,
    [switch]$CreateAdmin,
    [switch]$NoReload
)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$requirementsPath = Join-Path $projectRoot 'requirements.txt'
$stampPath = Join-Path $projectRoot '.venv\classlib-requirements.sha256'

# Process-only overrides: local commands always use SQLite and local files.
$localEnvironment = @{
    DATABASE_URL = $null
    SUPABASE_URL = $null
    SUPABASE_SERVICE_ROLE_KEY = $null
    SUPABASE_BUCKET = $null
    VERCEL = $null
    DJANGO_SETTINGS_MODULE = 'config.settings'
    DJANGO_DEBUG = '1'
    DJANGO_SECRET_KEY = 'django-insecure-local-development-only'
    DJANGO_ALLOWED_HOSTS = 'localhost,127.0.0.1,testserver'
    DJANGO_CSRF_TRUSTED_ORIGINS = "http://localhost:$Port,http://127.0.0.1:$Port"
    PYTHONUTF8 = '1'
}
$previousEnvironment = @{}
foreach ($name in $localEnvironment.Keys) {
    $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}

function Invoke-LocalPython {
    param([string[]]$PythonArguments)
    & $pythonPath @PythonArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed (exit $LASTEXITCODE): $($PythonArguments -join ' ')"
    }
}

Push-Location -LiteralPath $projectRoot
try {
    foreach ($name in $localEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $localEnvironment[$name], 'Process')
    }

    if (-not (Test-Path -LiteralPath $pythonPath)) {
        $basePython = Get-Command python.exe -ErrorAction SilentlyContinue
        if (-not $basePython) {
            throw 'Python 3.10 or newer is required. Install Python and run this script again.'
        }
        & $basePython.Source -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.10 or newer is required.' }
        & $basePython.Source -m venv (Join-Path $projectRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the local virtual environment.' }
    }

    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        $requirementsHash = [BitConverter]::ToString($hasher.ComputeHash([IO.File]::ReadAllBytes($requirementsPath)))
    } finally {
        $hasher.Dispose()
    }
    $installedHash = if (Test-Path -LiteralPath $stampPath) {
        (Get-Content -LiteralPath $stampPath -Raw).Trim()
    } else { '' }
    if (-not $SkipInstall -and $requirementsHash -ne $installedHash) {
        Invoke-LocalPython -PythonArguments @('-m', 'pip', 'install', '-r', $requirementsPath)
        Set-Content -LiteralPath $stampPath -Value $requirementsHash -Encoding ASCII
    }

    # Fail before migrating if the effective backend is unexpectedly remote.
    Invoke-LocalPython -PythonArguments @('-c', "from django.conf import settings; assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3'; assert not settings.SUPABASE_URL; print('Local mode: SQLite + private_files')")
    Invoke-LocalPython -PythonArguments @('manage.py', 'check')
    Invoke-LocalPython -PythonArguments @('manage.py', 'migrate', '--noinput')
    if ($CreateAdmin) {
        Invoke-LocalPython -PythonArguments @('manage.py', 'createsuperuser')
    }

    if ($SetupOnly) {
        Write-Host 'Local environment is ready.'
    } else {
        Write-Host "Open http://127.0.0.1:$Port/login/ in your browser. Press Ctrl+C to stop."
        $serverArguments = @('manage.py', 'runserver', "127.0.0.1:$Port")
        if ($NoReload) { $serverArguments += '--noreload' }
        Invoke-LocalPython -PythonArguments $serverArguments
    }
} finally {
    foreach ($name in $previousEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], 'Process')
    }
    Pop-Location
}
