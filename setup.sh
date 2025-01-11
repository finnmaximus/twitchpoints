#!/bin/bash
echo "🚀 Instalando Google Chrome en Koyeb..."

mkdir -p /app/.apt
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /app/.apt/chrome.deb
dpkg-deb -x /app/.apt/chrome.deb /app/.apt/

echo "✅ Google Chrome instalado en /app/.apt/opt/google/chrome/google-chrome"

# Agregar Chrome al PATH
export PATH="/app/.apt/opt/google/chrome:$PATH"

echo "🔄 Ejecutando el bot..."
exec python main.py