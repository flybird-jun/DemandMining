#!/bin/bash
# 任一命令失败立刻退出，避免半残数据库/半残 .env
set -e

# ---------- 第一步：算出要写的文件最终路径 ----------
# $0 是脚本自身的路径。dirname 取它的目录名。
# cd ... && pwd 是把相对路径转成绝对路径。
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# scripts 的上一层就是项目根目录
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 配置文件最终会写到这两个位置
ENV_FILE="$PROJECT_ROOT/.env"
ENV_TEST_FILE="$PROJECT_ROOT/.env.test"

# ---------- 第二步：定义配置项清单 ----------
# 每行是 "变量名|中文提示"，用 | 分隔。
# 想新增一项？只要在下面末尾追加一行即可，不用改别的地方。
CFG_ITEMS=(
    "llm_api_url|大模型URL"
    "llm_api_key|大模型API_KEY"
    "llm_model|大模型model"
    "slm_api_url|小模型URL"
    "slm_api_key|小模型API_KEY"
    "slm_model|小模型model"
    "embedding_api_url|向量模型URL"
    "embedding_api_key|向量模型API_KEY"
    "embedding_model|向量模型model"
    "data_path|采集数据目录"
    "pg_port|postgres端口号, 如果没有创建cluster, 输入回车"
    "pg_user|postgres用户名"
    "pg_user_passwd|postgres用户密码"
    "pg_database|postgres数据库实例名"
    "pg_test_database|postgres数据库测试实例名"
)
CFG_TEST_ITEMS=(
    "pg_test_database"
)
function collect_configs() {
    # 第 1 个参数：要回填的关联数组名（通过 nameref 写回）
    # 第 2 个参数：分类描述，只用于显示，例如 "生产" 或 "测试"
    local -n cfg_ref="$1"

    echo "==== 环境配置 ===="
    echo "是否现在设置配置项, Y/N:"
    read answer             # 等待用户从键盘输入，回车结束

    # 把用户输入统一转成小写，方便比较 y / yes
    # tr 'A-Z' 'a-z' 表示把所有大写字母换成小写字母
    answer=$(echo "$answer" | tr 'A-Z' 'a-z')

    if [ "$answer" = "y" ] || [ "$answer" = "yes" ]; then
        # ---- 用户选择"现在设置"：遍历每一项配置，逐个问 ----
        # "${CFG_ITEMS[@]}" 表示把数组的每一个元素都拿出来
        for item in "${CFG_ITEMS[@]}"; do
            # cut -d'|' 表示按 | 切分；-f1 取第 1 段，-f2 取第 2 段
            cfg_name=$(echo "$item" | cut -d'|' -f1)
            cfg_desc=$(echo "$item" | cut -d'|' -f2)

            echo "请输入${cfg_desc}:"
            read v
            cfg_ref["$cfg_name"]="$v"
        done
    else
        # ---- 用户选择"跳过"：每项留空 ----
        for item in "${CFG_ITEMS[@]}"; do
            cfg_name=$(echo "$item" | cut -d'|' -f1)
            cfg_ref["$cfg_name"]=""
        done
    fi
}

# ---------- 第四步：定义写出函数 ----------
# 函数的作用：把关联数组里所有的 key 都写到指定文件（顺序按数组当前顺序）。
# 调用方需要传一个已 collect 过的关联数组进来。
# 用法：write_configs prod_cfg "$ENV_FILE"
function write_configs() {
    # 第 1 个参数：要写出的关联数组名（通过 nameref 读取）
    # 第 2 个参数：要写入的文件路径
    local -n cfg_ref="$1"
    local out_file="$2"

    # 用 : > 文件名 这种写法先清空文件（冒号是真值命令，重定向只起副作用）
    : > "$out_file"
    # 遍历关联数组里所有 key，把收集到的每一项都写出去
    # 这样 cfg["PYTHONDONTWRITEBYTECODE"]=1 这类额外塞进来的值也会被保留
    for key in "${!cfg_ref[@]}"; do
        echo "${key} = ${cfg_ref[$key]}" >> "$out_file"
    done
}

function install_postgres() {
	local -n cfg_ref="$1"
	# /usr/lib/postgresql/ 下可能有多个版本（升级残留），取数字排序后的最大值
    pg_version=$(ls /usr/lib/postgresql/ | sort -V | tail -1)
    if command -v psql >/dev/null 2>&1; then
        echo "PostgreSQL 已安装"
    else
        sudo apt update
        sudo apt install -y postgresql postgresql-contrib
        echo "PostgreSQL 安装完成"
        # 设置开机自启动
        sudo systemctl enable postgresql
		# 安装pg-vector
		sudo apt install -y curl ca-certificates gnupg
		curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /usr/share/keyrings/postgresql.gpg
		echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt jammy-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list
		sudo apt update
		sudo apt install postgresql-${pg_version}-pgvector
    fi

    # 创建数据库集群实例
	if [[ ${cfg_ref['pg_port']} == "" ]];then
		cluster_name=$(pwd | tr '/' '_')
		# 已存在同名 cluster 就跳过创建，只查端口；不存在才新建
		if sudo pg_lsclusters $pg_version $cluster_name >/dev/null 2>&1; then
			echo "Cluster $pg_version/$cluster_name 已存在, 复用"
		else
			sudo pg_createcluster $pg_version $cluster_name
		fi
		# 拉起数据库集群实例
		sudo pg_ctlcluster $pg_version $cluster_name start
		# 查看数据库集群端口号
		cfg_ref['pg_port']=$(sudo pg_lsclusters $pg_version $cluster_name | awk 'NR==2 {print $3}')
		# 创建用户和database
		# 用 psql -c 多条命令的形式跑，不再依赖 heredoc 的 tab 缩进约定
		# _esc 把字符串里的单引号转成 PostgreSQL 字符串字面量要求的两个单引号 ''''
		# 防止密码/用户名里含 ' 时把 SQL 切断、以及避免最朴素的注入
		_esc() { printf "%s" "$1" | sed "s/'/''/g"; }
		sudo -u postgres psql -c "CREATE USER $(_esc "${cfg_ref['pg_user']}") WITH PASSWORD '$(_esc "${cfg_ref['pg_user_passwd']}")';" \
		                       -c "CREATE DATABASE $(_esc "${cfg_ref['pg_database']}") OWNER $(_esc "${cfg_ref['pg_user']}");" \
		                       -c "CREATE DATABASE $(_esc "${cfg_ref['pg_test_database']}") OWNER $(_esc "${cfg_ref['pg_user']}");"
	fi
	
    echo "数据库创建完成"
}

# 生产环境：先收集到关联数组，最后再统一写出
declare -A cfg
collect_configs cfg
# 安装python venv虚拟环境
python -m venv .venv
source .venv/bin/activate

# Python项目安装到Python环境中
pip install -e .
# 安装环境依赖
pip install -r requirements.txt
# 安装postgres

install_postgres cfg

cfg["PYTHONDONTWRITEBYTECODE"]=1

# 移除cfg中的pg_test_database, 保存到test_cfg
declare -A test_cfg

for item in "${CFG_TEST_ITEMS[@]}"; do
	test_cfg[$item]="${cfg[$item]}"
	unset 'cfg[$item]'
done

write_configs cfg "$ENV_FILE"
write_configs test_cfg "$ENV_TEST_FILE"