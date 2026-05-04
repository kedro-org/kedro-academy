"""
Generate synthetic user data for risk profile classification.

Run this script to create training data:
    python generate_data.py
"""

import numpy as np
import pandas as pd
#from pathlib import Path
#from mlrun.artifacts import DatasetArtifact


def generate_user_data(n_samples=1000, random_state=42):
    """Generate synthetic user data for risk profile classification.
    
    Args:
        n_samples: Number of samples to generate.
        random_state: Random seed for reproducibility.
        
    Returns:
        DataFrame with user features and risk profile labels.
    """
    np.random.seed(random_state)
    
    # Generate synthetic user data
    data = {
        "user_id": [f"USER_{i:05d}" for i in range(n_samples)],
        "age": np.random.randint(18, 80, n_samples),
        "income": np.random.randint(20000, 200000, n_samples),
        "investment_experience_years": np.random.randint(0, 40, n_samples),
        "savings_ratio": np.random.uniform(0.05, 0.5, n_samples),
        "debt_ratio": np.random.uniform(0.0, 0.6, n_samples),
        "risk_tolerance_score": np.random.randint(1, 11, n_samples),
        "portfolio_volatility": np.random.uniform(0.05, 0.4, n_samples),
    }
    
    df = pd.DataFrame(data)
    
    # Create risk profile labels based on features
    # Conservative: low risk tolerance, high savings, low volatility
    # Moderate: medium risk tolerance and balanced features
    # Aggressive: high risk tolerance, younger, higher volatility
    conditions = [
        (df["risk_tolerance_score"] <= 3) & (df["portfolio_volatility"] < 0.15),
        (df["risk_tolerance_score"] >= 7) & (df["portfolio_volatility"] > 0.25),
    ]
    choices = ["conservative", "aggressive"]
    df["risk_profile"] = np.select(conditions, choices, default="moderate")
    
    return df


def main(context):
    """Generate and save training data."""
    print("Generating synthetic user data...")
    
    # Generate data
    df = generate_user_data(n_samples=1000, random_state=42)
    
    # Create output directory
    #output_dir = Path(__file__).parent / "data" / "raw"
    #output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save to CSV
    #output_file = output_dir / "user_data.csv"
    #df.to_csv(output_file, index=False)


    # log it
    context.log_dataset(
        key="user_data.csv",
        df=df,
        artifact_path="v3io:///projects/my-project/artifacts/",
        upload=True,
        format="csv",
    )

    print(f"✓ Generated {len(df)} samples")
    print(f"\nRisk Profile Distribution:")
    print(df["risk_profile"].value_counts().to_dict())
    
    # Display sample
    print(f"\nSample data (first 5 rows):")
    print(df.head())
    
    # Display statistics
    print(f"\nFeature Statistics:")
    print(df.describe())


if __name__ == "__main__":
    main()

