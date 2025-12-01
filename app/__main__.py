try:
    # 优先绝对导入，兼容打包/解释器不同运行环境
    from app.main import main  # type: ignore
except Exception:  # 回退在包内相对导入
    from .main import main  # type: ignore


if __name__ == "__main__":
    main()


