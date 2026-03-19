import polybench

cfg = polybench.RunConfig(
    difficulty="hard",
    opponents=7,
    games=1,
    llm_provider="kaggle",
    llm_model="google/gemini-2.5-flash",
)

polybench.run_benchmark(cfg)
