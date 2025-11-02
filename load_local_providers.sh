current_dir=$(pwd)
script_dir=$(cd "$(dirname "$0")" && pwd)

cd "$script_dir/agent-starter-python"

echo "Current dir: $(pwd)"
data_path="$script_dir/data/providerlist.json"
echo "Using data path: $data_path"

uv run python src/postgres_loader.py "$data_path"

cd "$current_dir"