#!/usr/bin/env pwsh
# Script to run the pipeline with HuggingFace token

param(
    [Parameter(Mandatory=$true)]
    [string]$HFToken,
    
    [Parameter(Mandatory=$false)]
    [string]$VideoPath = "D:\Onedrive\Documents\Zoom\2026-02-11 09.14.57 Shyam Jayachandran's Zoom Meeting\video1933084732.mp4",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "C:\Users\sivan\Downloads\webex-speaker-labeling\output",
    
    [Parameter(Mandatory=$false)]
    [string]$FFmpegPath = "C:\Users\sivan\Downloads\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
)

# Set the HuggingFace token for this session
$env:HF_TOKEN = $HFToken

# Verify it's set
Write-Host "HF_TOKEN is now set for this session" -ForegroundColor Green

# Run the pipeline
Write-Host "Starting pipeline..." -ForegroundColor Cyan
.\venv\Scripts\python.exe .\process_meeting.py `
    --video "$VideoPath" `
    --output-dir "$OutputDir" `
    --ffmpeg-path "$FFmpegPath"

$exitCode = $LASTEXITCODE
if ($exitCode -eq 0) {
    Write-Host "Pipeline completed successfully!" -ForegroundColor Green
} else {
    Write-Host "Pipeline failed with exit code: $exitCode" -ForegroundColor Red
}

exit $exitCode
