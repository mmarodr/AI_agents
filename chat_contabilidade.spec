# -*- mode: python ; coding: utf-8 -*-

import shutil
import os

a = Analysis(
    ['app.py'],
    pathex=['Petrobras_AI_Agents'],
    binaries=[],
    datas=[
        ('./templates', 'templates'),                # Caminho para a pasta templates
        ('./static', 'static'),                      # Caminho para a pasta static
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='chat_contabilidade',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='chat_contabilidade',
)

# Script de pós-processamento para copiar arquivos adicionais
dist_dir = os.path.join("dist", "chat_contabilidade")

# Função para copiar uma pasta inteira
def copy_folder(src, dest):
    if os.path.exists(src):
        shutil.copytree(src, dest, dirs_exist_ok=True)

# Função para copiar um arquivo
def copy_file(src, dest):
    if os.path.exists(src):
        shutil.copy2(src, dest)

# Copiando pastas e arquivos necessários para a pasta de distribuição
copy_folder("templates", os.path.join(dist_dir, "templates"))
copy_folder("static", os.path.join(dist_dir, "static"))
copy_folder("config_json/databricks", os.path.join(dist_dir, "config_json/databricks"))
copy_file(".env", dist_dir)
copy_file("petrobras-ca-root.pem", dist_dir)