$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# Banco descartavel do runner, acessivel somente via loopback.
$mongoVersion = '8.0.16'
$mongoRoot = Join-Path $env:RUNNER_TEMP 'assessoria-ci-mongodb'
$archivePath = Join-Path $mongoRoot 'mongodb.zip'
$dataPath = Join-Path $mongoRoot 'data'
$logPath = Join-Path $mongoRoot 'mongodb.log'
New-Item -ItemType Directory -Path $dataPath -Force | Out-Null

$downloadUrl = "https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-$mongoVersion.zip"
Invoke-WebRequest -Uri $downloadUrl -OutFile $archivePath
Expand-Archive -LiteralPath $archivePath -DestinationPath $mongoRoot -Force
$mongodPath = Join-Path $mongoRoot "mongodb-win32-x86_64-windows-$mongoVersion/bin/mongod.exe"
if (-not (Test-Path -LiteralPath $mongodPath)) {
    throw 'Executavel mongod nao encontrado no pacote oficial.'
}

$mongoProcess = Start-Process -FilePath $mongodPath -ArgumentList @(
    '--dbpath', "`"$dataPath`"",
    '--logpath', "`"$logPath`"",
    '--bind_ip', '127.0.0.1',
    '--port', '27017'
) -WindowStyle Hidden -PassThru
"CI_MONGODB_PID=$($mongoProcess.Id)" | Out-File -FilePath $env:GITHUB_ENV -Append -Encoding utf8

for ($attempt = 0; $attempt -lt 30; $attempt++) {
    if ($mongoProcess.HasExited) {
        if (Test-Path -LiteralPath $logPath) { Get-Content -LiteralPath $logPath -Tail 30 }
        throw 'MongoDB encerrou antes de ficar disponivel.'
    }
    python -c "import os; from pymongo import MongoClient; c = MongoClient(os.environ['MONGODB_URI'], serverSelectionTimeoutMS=1000); c.admin.command('ping'); c.close()" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Output 'MongoDB temporario pronto.'
        exit 0
    }
    Start-Sleep -Seconds 1
}
if (Test-Path -LiteralPath $logPath) { Get-Content -LiteralPath $logPath -Tail 30 }
throw 'MongoDB nao ficou disponivel dentro do prazo.'
