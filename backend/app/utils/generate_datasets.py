import csv
import os
import random
from typing import List, Tuple

"""
This module programmatically generates the expanded training (600 records)
and benchmark (150 records) datasets for TERA, using a task-complexity-based
labeling policy. The ground-truth cheap model success labels are derived from
semantic domain and difficulty characteristics rather than lexical features.
"""

# Base success probabilities per domain tag
DOMAIN_BASE_SUCCESS = {
    "translate": 0.85,
    "gen": 0.75,     # summarization, extraction, creative, knowledge
    "json": 0.65,
    "logic": 0.50,   # classification, logical reasoning
    "math": 0.35,
    "code": 0.30
}

# Domain tag mappings for the 10 task domains
TASK_DOMAINS = {
    "math": "math",
    "code": "code",
    "logic": "logic",
    "translate": "translate",
    "summarize": "gen",
    "extract": "gen",
    "classify": "logic",
    "json": "json",
    "creative": "gen",
    "knowledge": "gen"
}

def generate_prompt_pool(rng: random.Random, domain: str, count: int) -> List[Tuple[str, str, int]]:
    """
    Generates a list of (prompt, difficulty, label) for a specific task domain.
    """
    prompts = []
    
    # We divide the requested count equally into easy, medium, and hard prompts
    chunk = count // 3
    extra = count % 3
    
    difficulties = ["easy"] * chunk + ["medium"] * chunk + ["hard"] * (chunk + extra)
    
    # Define various templates and parameters for randomization
    cities = ["Paris", "Tokyo", "London", "Berlin", "New York", "Sydney", "Rome", "Toronto", "Beijing", "Cairo"]
    names = ["John", "Sarah", "Emily", "Michael", "David", "Jessica", "Alex", "Sophia", "Robert", "Emma"]
    languages = ["Spanish", "French", "German", "Japanese", "Chinese", "Italian", "Portuguese", "Russian", "Arabic", "Korean"]
    topics = ["clean energy", "artificial intelligence", "space exploration", "inflation rates", "quantum physics", "macroeconomics", "organic chemistry", "renaissance art"]
    
    base_prob = DOMAIN_BASE_SUCCESS[TASK_DOMAINS[domain]]
    
    for i, diff in enumerate(difficulties):
        prompt = ""
        # Diff-based probability adjustments
        if diff == "easy":
            p_adj = 0.10
        elif diff == "medium":
            p_adj = 0.00
        else: # hard
            p_adj = -0.20
            
        p_success = max(0.05, min(0.95, base_prob + p_adj))
        # Determine label deterministically using the rng seed
        label = 1 if rng.random() < p_success else 0
        
        # Unique identifier/index to keep prompts unique
        uid = i + 1
        
        if domain == "math":
            if diff == "easy":
                prompt = f"calculate: Solve this basic linear equation: {uid * 2}x + {uid * 5} = {uid * 20}"
            elif diff == "medium":
                prompt = f"calculate: Solve this quadratic equation: x^2 + {uid * 3}x - {uid * 4} = 0 and find both real roots."
            else:
                prompt = f"calculate: Evaluate the definite integral of x * sin({uid}x) from 0 to pi, showing all integration by parts steps."
                
        elif domain == "code":
            if diff == "easy":
                prompt = f"code: Write a Python function to check if the number {uid * 13} is prime."
            elif diff == "medium":
                prompt = f"code: Implement a Python class representing a Binary Search Tree with insert and search methods for node {uid}."
            else:
                prompt = f"code: Design a multi-threaded web crawler in C++ that respects robots.txt and uses a thread pool of size {uid + 2}."
                
        elif domain == "logic":
            if diff == "easy":
                prompt = f"explain: If box A is inside box B, and box B is inside box C, is box A inside box C? (ID: {uid})"
            elif diff == "medium":
                prompt = f"explain: A farmer needs to cross a river with a wolf, a goat, and a cabbage. If left alone, the wolf eats goat, or goat eats cabbage. Explain the steps to cross safely. (ID: {uid})"
            else:
                prompt = f"explain: Analyze this knights and knaves puzzle: Knight A says 'B is a knave'. Knight B says 'A and I are of opposite types'. What are they? (ID: {uid})"
                
        elif domain == "translate":
            lang = languages[uid % len(languages)]
            if diff == "easy":
                prompt = f"translate: Translate this short phrase to {lang}: 'Good morning, where is the hotel?'"
            elif diff == "medium":
                prompt = f"translate: Translate the following formal business email to {lang}: 'Dear Sir, we are writing to confirm that your shipment has been delivered successfully. Please sign the attached invoice.'"
            else:
                prompt = f"translate: Translate this philosophical text to {lang}: 'All human beings are born free and equal in dignity and rights. They are endowed with reason and conscience and should act towards one another in a spirit of brotherhood.'"
                
        elif domain == "summarize":
            topic = topics[uid % len(topics)]
            if diff == "easy":
                prompt = f"summarize: Shorten this short statement about {topic}: 'The quick development of technologies has changed our daily routines in many unexpected ways.'"
            elif diff == "medium":
                prompt = f"summarize: Write a single-sentence summary of this paragraph about {topic}: 'Greenhouse gas emissions continue to rise globally, exacerbating extreme weather patterns. Experts emphasize that transitioning to renewable sources is critical to prevent rising sea levels.'"
            else:
                prompt = f"summarize: Write a comprehensive executive summary of this article about {topic}: '{topic.capitalize()} has witnessed a massive influx of funding. Major institutions are upgrading their infrastructure. However, regulatory frameworks remain underdeveloped, posing severe risks for retail consumers and systemic stability.'"
                
        elif domain == "extract":
            city = cities[uid % len(cities)]
            name = names[uid % len(names)]
            if diff == "easy":
                prompt = f"extract: Find the city in this text: 'We are traveling to {city} next week.'"
            elif diff == "medium":
                prompt = f"extract: Retrieve all names and emails from this list: '1. {name} - {name.lower()}@example.com; 2. Alice - alice@example.org'."
            else:
                prompt = f"extract: Parse this scientific abstract to extract all chemical compounds, their experimental melting points, and associated error bounds: 'We observed compound {name}X melting at {uid * 20}C +/- 1.5C, while compound {name}Y melted at {uid * 35}C +/- 2.0C.'"
                
        elif domain == "classify":
            if diff == "easy":
                prompt = f"classify: Is this positive or negative: 'This product is absolute garbage!' (ID: {uid})"
            elif diff == "medium":
                prompt = f"classify: Categorize the news headline: 'Tech giant launches new AI assistant with voice capabilities' into tech, business, politics, or sports."
            else:
                prompt = f"classify: Perform multi-label classification on this customer feedback transcript: 'The customer service agent was very polite, but the product was delivered late and arrived damaged. I demand a full refund immediately.'"
                
        elif domain == "json":
            if diff == "easy":
                prompt = f"json: Generate a simple JSON object representing a book with fields 'title' and 'author' (ID: {uid})."
            elif diff == "medium":
                prompt = f"json: Generate a valid JSON schema representing a user profile containing email validation and nested address fields (ID: {uid})."
            else:
                prompt = f"json: Create a complex nested JSON schema for an inventory management system order with recursive reference arrays, currency constraints, and status enums (ID: {uid})."
                
        elif domain == "creative":
            topic = topics[uid % len(topics)]
            if diff == "easy":
                prompt = f"code: Write a short haiku about {topic}."
            elif diff == "medium":
                prompt = f"code: Draft a four-stanza poem about the concept of {topic} and the flow of time."
            else:
                prompt = f"code: Write a complete movie script scene set in a base on Mars, including character dialogues, stage directions, and audio cues about {topic}."
                
        elif domain == "knowledge":
            city = cities[uid % len(cities)]
            if diff == "easy":
                prompt = f"explain: What is the capital city of {city}'s country?"
            elif diff == "medium":
                prompt = f"explain: Explain the biological process of photosynthesis and how light energy is captured by chlorophyll."
            else:
                prompt = f"explain: Detail the historical timeline, key political agreements, and structural consequences of the Treaty of Versailles signed in 1919."
                
        prompts.append((prompt, str(label), TASK_DOMAINS[domain]))
        
    return prompts

def generate_and_save_datasets() -> None:
    """
    Generates and saves the training (600 prompts) and benchmark (150 prompts) datasets.
    """
    # Fix the random seeds for absolute reproducibility
    train_rng = random.Random(101)
    bench_rng = random.Random(202)
    
    # 1. Generate Training Dataset (600 prompts: 60 per domain)
    train_data = []
    for domain in TASK_DOMAINS.keys():
        train_data.extend(generate_prompt_pool(train_rng, domain, 60))
        
    # Shuffle training data to mix domains
    train_rng.shuffle(train_data)
    
    # 2. Generate Benchmark Dataset (150 prompts: 15 per domain)
    bench_data = []
    for domain in TASK_DOMAINS.keys():
        bench_data.extend(generate_prompt_pool(bench_rng, domain, 15))
        
    bench_rng.shuffle(bench_data)
    
    # Write to files
    base_path = os.path.dirname(__file__)
    
    # Training path: backend/app/training/sample_dataset.csv
    train_path = os.path.abspath(os.path.join(base_path, "../training/sample_dataset.csv"))
    # Benchmark path: backend/app/evaluation/sample_benchmark.csv
    bench_path = os.path.abspath(os.path.join(base_path, "../evaluation/sample_benchmark.csv"))
    
    os.makedirs(os.path.dirname(train_path), exist_ok=True)
    os.makedirs(os.path.dirname(bench_path), exist_ok=True)
    
    with open(train_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["prompt", "label", "domain"])
        writer.writerows(train_data)
        
    with open(bench_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["prompt", "label", "domain"])
        writer.writerows(bench_data)
        
    print("====================================================")
    print("Dataset generation completed successfully.")
    print(f"Training dataset written to:  {train_path} ({len(train_data)} rows)")
    print(f"Benchmark dataset written to: {bench_path} ({len(bench_data)} rows)")
    print("====================================================")

if __name__ == "__main__":
    generate_and_save_datasets()
