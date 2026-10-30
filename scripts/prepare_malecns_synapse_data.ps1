$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

$data = Join-Path $root "data\malecns"
New-Item -ItemType Directory -Force -Path $data | Out-Null
$base = "https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome"
$files = @(
    @{ Name = "body-annotations-male-cns-v1.0-minconf-0.5.feather"; Bytes = 14483314; MD5 = "50a7718770c57220f160ba4f431ab89e" },
    @{ Name = "body-neurotransmitters-male-cns-v1.0.feather"; Bytes = 43282834; MD5 = "3d842b12fe5c49eefade528d7dd24a1f" },
    @{ Name = "connectome-weights-male-cns-v1.0-minconf-0.5.feather"; Bytes = 1051241946; MD5 = "f30e9dcca25cfd021bf1e7b3d975599e" },
    @{ Name = "syn-partners-male-cns-v1.0-minconf-0.5.feather"; Bytes = 6777179098; MD5 = "58efcf712f8c4d4de5f2ad51e97def76" },
    @{ Name = "syn-points-male-cns-v1.0-minconf-0.5.feather"; Bytes = 13061489098; MD5 = "c69d08758de07582035cc8843574493a" },
    @{ Name = "tbar-neurotransmitters-male-cns-v1.0.feather"; Bytes = 2651680218; MD5 = "51b02c11690662aedef28f86d394ff0d" }
)
foreach ($file in $files) {
    $destination = Join-Path $data $file.Name
    if (-not (Test-Path -LiteralPath $destination) -or (Get-Item -LiteralPath $destination).Length -ne $file.Bytes) {
        Write-Output "Downloading or resuming $($file.Name)"
        & curl.exe -L --fail --retry 8 --retry-delay 5 --continue-at - --output $destination "$base/$($file.Name)"
        if ($LASTEXITCODE -ne 0) { throw "Download failed: $($file.Name)" }
    }
    if ((Get-Item -LiteralPath $destination).Length -ne $file.Bytes) { throw "Size mismatch: $($file.Name)" }
    $hash = (Get-FileHash -LiteralPath $destination -Algorithm MD5).Hash.ToLowerInvariant()
    if ($hash -ne $file.MD5) { throw "Checksum mismatch for $($file.Name): $hash" }
    Write-Output "Verified $($file.Name)"
}

& python (Join-Path $root "scripts\extract_verified_odor_motor_path.py")
if ($LASTEXITCODE -ne 0) { throw "Pathway extraction failed" }
& python (Join-Path $root "scripts\export_portable_runtime.py")
if ($LASTEXITCODE -ne 0) { throw "Portable runtime export failed" }
& python (Join-Path $root "scripts\enrich_verified_pathway_synapses.py")
if ($LASTEXITCODE -ne 0) { throw "Synapse evidence extraction failed" }
& python (Join-Path $root "scripts\validate_verified_pathway.py")
if ($LASTEXITCODE -ne 0) { throw "Pathway validation failed" }
