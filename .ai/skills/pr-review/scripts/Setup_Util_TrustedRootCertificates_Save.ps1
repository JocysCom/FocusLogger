# The hostname from which to retrieve the corporate certificate
$HostNames = @('login.microsoftonline.com')
$Port = 443

# Save the corporate root certificates and individual .crt files under
# {repo}\.tmp\trusted_root_certificates\. .tmp/ is local-only (matched by the
# *.tmp gitignore rule), so per-developer cert state never gets committed.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Locate the repo root by walking up from this script until we find .git.
# This script is synced into multiple agent skill folders at varying depths,
# so we don't hardcode a relative path.
$RepoRoot = $ScriptDir
while ($RepoRoot) {
    if (Test-Path (Join-Path $RepoRoot '.git')) { break }
    $parent = Split-Path $RepoRoot -Parent
    if (-not $parent -or $parent -eq $RepoRoot) { $RepoRoot = $null; break }
    $RepoRoot = $parent
}
if (-not $RepoRoot) {
    Write-Warning "Repo root (.git folder) not found above $ScriptDir; falling back to script-local Files\."
    $OutputDir = Join-Path $ScriptDir 'Files'
} else {
    $OutputDir = Join-Path $RepoRoot '.tmp\trusted_root_certificates'
}
$OutputPemFile = Join-Path $OutputDir 'trusted_root_certificates.pem'

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "Created directory: $OutputDir"
}

# Use SslStream callback to ignore SSL errors per connection
$PemCerts = @()
$Index = 0
$SeenThumbs = @()

foreach ($HostName in $HostNames) {
	$HostAdded = $false
	# Create a TCP client and connect to the specified host and port
	$TcpClient = New-Object System.Net.Sockets.TcpClient
	$TcpClient.Connect($HostName, $Port)
	# Create an SSL stream that will close the client's stream
	$SslStream = New-Object System.Net.Security.SslStream(
		$TcpClient.GetStream(),
		$true,
		[System.Net.Security.RemoteCertificateValidationCallback] { param($sender, $certificate, $chain, $sslPolicyErrors) return $true },
		$null
	)
	Write-Host "Performing SSL handshake for $HostName"
	$SslStream.AuthenticateAsClient($HostName)
	# Build the certificate chain
	$Chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
	$Chain.Build($SslStream.RemoteCertificate) | Out-Null
	foreach ($Element in $Chain.ChainElements) {
		# Avoid saving the end-entity certificate
		if ($Element.Certificate -ne $SslStream.RemoteCertificate) {
			$thumb = $Element.Certificate.Thumbprint
			if ($SeenThumbs -notcontains $thumb) {
				$SeenThumbs += $thumb
				if (-not $HostAdded) {
					Write-Host $HostName
					$HostAdded = $true
				}
				# Export certificate
				$CertData = $Element.Certificate.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert)
				$PemData = [System.Convert]::ToBase64String($CertData, 'InsertLineBreaks')
				$PemCert = "-----BEGIN CERTIFICATE-----`n$PemData`n-----END CERTIFICATE-----"
				$PemCerts += $PemCert
				$Index++
				$IndividualFile = Join-Path -Path (Split-Path $OutputPemFile) -ChildPath ("trusted_root_certificates_$Index.crt")
				Set-Content -Path $IndividualFile -Value $PemCert -Encoding ASCII
				# Output concise certificate info
				$cn = $Element.Certificate.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::SimpleName, $false)
				$issuer = $Element.Certificate.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::SimpleName, $true)
				$type = if ($Element.Certificate.Subject -eq $Element.Certificate.Issuer) { 'Root CA' } else { 'Intermediate CA' }
				Write-Host "  - [$type] CN=$cn, Issuer=$issuer"
			}
		}
	}
	# Clean up streams
	$SslStream.Close()
	$TcpClient.Close()
}

# Write consolidated PEM file
Set-Content -Path $OutputPemFile -Value ($PemCerts -join "`n`n") -Encoding ASCII
Write-Host "Trusted root certificates saved to $OutputPemFile"
# Set environment variables for certificate bundle for various tools
$certFile = $OutputPemFile
if (Test-Path $certFile) {
    $env:REQUESTS_CA_BUNDLE = $certFile
    $env:CURL_CA_BUNDLE = $certFile

    Write-Host "Setting certificate bundle environment variables..." -ForegroundColor Green
    Write-Host "REQUESTS_CA_BUNDLE: $env:REQUESTS_CA_BUNDLE" -ForegroundColor Gray
    Write-Host "CURL_CA_BUNDLE: $env:CURL_CA_BUNDLE" -ForegroundColor Gray
    Write-Host ""
}
