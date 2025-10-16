# run_month.py
import os
import yaml
from charts import run_from_config

def main():
    # 明确切换到月报命名空间
    os.environ["SPC_SCOPE"] = "month"
    # 读取月报配置
    with open("spc_config_month.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    # 复用既有主流程
    run_from_config(cfg)

if __name__ == "__main__":
    main()
