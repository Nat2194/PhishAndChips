@echo off
echo ===================================================
echo   PhishAndChips - Verification de l'environnement
echo ===================================================

IF NOT EXIST "venv\Scripts\activate.bat" (
    echo [INFO] Creation du Virtual Environment venv...
    python -m venv venv
    echo [INFO] Activation et mise a jour de pip...
    call venv\Scripts\activate
    python -m pip install --upgrade pip
    echo [INFO] Installation des dependances...
    pip install cryptography
    pip install -r api\src\python\conf\requirements.txt
) ELSE (
    echo [OK] Environnement virtuel venv detecte.
)

echo.
echo [INFO] Verification des secrets et certificats...
call venv\Scripts\activate
cd docker
python init_secrets.py
cd ..

echo.
echo ===================================================
echo   Lancement des conteneurs avec Docker Compose...
echo ===================================================
cd docker
docker-compose up -d
cd ..

echo.
echo ===================================================
echo   Termine ! Vous pouvez tester l'application locale.
echo ===================================================
pause