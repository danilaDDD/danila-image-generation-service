if [ "$#" -gt 0 ]; then
  python commands.py add_primary_token --name test --token $1
  uvicorn app.main:app --host 0.0.0.0 --port 8000
else
  echo "input primary token is empty!"
fi

