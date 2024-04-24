# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['-', 'Science', 'and', 'Technology', 'Facilities', 'Council\\Documents\\magnet', 'lab', 'control\\20220906', 'Hall', 'probe', 'bench', 'controls', 'mainGUI.py'],
             pathex=['C:\\Users\\itx75623\\OneDrive'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=['motor_controller_PM1000.py', 'HP_bench_GUI.py', 'teslameter_select_GUI.py', 'magnet_lab_GUI_images_rc.py', 'teslameter_3MTS.py'],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,  
          [],
          name='-',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )
