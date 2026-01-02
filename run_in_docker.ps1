# Build and run the Docker image, writing outputs to ./output
# Usage: Open PowerShell in repository root and run: .\run_in_docker.ps1
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]
    $RemainingArgs,
    [switch]
    $NoBuild,
    [switch]
    $Rebuild
)

$repo = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
Set-Location $repo

# Image name used for build/run when creating or using existing image
$ImageName = 'qrcode-logo:local'

# Normalize long-form flags passed as --no-build or --rebuild in RemainingArgs
if ($RemainingArgs -and $RemainingArgs.Count -gt 0) {
    $cleanArgs = @()
    foreach ($a in $RemainingArgs) {
        if ($a -eq '--no-build') { $NoBuild = $true; continue }
        if ($a -eq '--rebuild') { $Rebuild = $true; continue }
        $cleanArgs += $a
    }
    $RemainingArgs = $cleanArgs
}

if (-not (Test-Path -Path "output")) {
    New-Item -ItemType Directory -Path output | Out-Null
}

if ($NoBuild) {
    Write-Host "Skipping docker build as requested (--no-build)"
    $imgId = (& docker images -q $ImageName) -join "" | ForEach-Object { $_.Trim() }
    if (-not $imgId) {
        Write-Error "Image '$ImageName' not found. Run without --no-build to build the image or use --rebuild."
        exit 1
    }
} else {
    $needBuild = $true
    if (-not $Rebuild) {
        $imgId = (& docker images -q $ImageName) -join "" | ForEach-Object { $_.Trim() }
        if ($imgId) {
            Write-Host "Using existing image '$ImageName' (skip build). Use --rebuild to force rebuild."
            $needBuild = $false
        }
    }

    if ($needBuild) {
        Write-Host "Building Docker image '$ImageName'..."
        $bproc = Start-Process -FilePath 'docker' -ArgumentList @('build','-t',$ImageName,'.') -NoNewWindow -Wait -PassThru
        if ($bproc.ExitCode -ne 0) {
            Write-Error "Docker build failed. Ensure Docker is installed and running."
            exit 1
        }
    }
}

Write-Host "Running container to generate files (host repo -> /app, outputs -> ./output)..."
# Map the host repo into the container at /app so the container reads config and logos from host.
$pwdPath = ${PWD}.Path

# Default args if none provided: use template mode and write outputs into /output on host
if ($RemainingArgs -and $RemainingArgs.Count -gt 0) {
    $pythonArgs = $RemainingArgs
} else {
    # Force template usage by default so the script always fills the provided SVG template
    $pythonArgs = @('--template','/app/template_pure.svg')
}

# Do not inject output paths here; let the generator derive output filenames
# from `qr_config.yaml` or CLI args so names remain consistent.

$dockerArgs = @('run','--rm','-v',"${pwdPath}:/app",'-v',"${pwdPath}\\output:/output",$ImageName,'python','/app/generate_qr_sheet.py') + $pythonArgs

$proc = Start-Process -FilePath 'docker' -ArgumentList $dockerArgs -NoNewWindow -Wait -PassThru
$exit = $proc.ExitCode

if ($exit -ne 0) {
    Write-Error "Docker run failed (exit code $exit)."
    exit 2
}

Write-Host "Done. See ./output for generated files."
