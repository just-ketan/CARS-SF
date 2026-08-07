import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

class ValidationPlots:
    """
    Generates research-grade visualizations for dataset validation.
    """
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    def generate_pca(self, df: pd.DataFrame, target_col: str = "service_class"):
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_cols) < 2:
            return
            
        X = df[numeric_cols].fillna(0)
        y = df[target_col] if target_col in df.columns else None
        
        # Subsample if too large
        if len(X) > 10000:
            idx = X.sample(10000).index
            X = X.loc[idx]
            if y is not None:
                y = y.loc[idx]
                
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)
        
        plt.figure(figsize=(10, 8))
        if y is not None:
            sns.scatterplot(x=X_pca[:, 0], y=X_pca[:, 1], hue=y, alpha=0.6, palette="Set2")
        else:
            sns.scatterplot(x=X_pca[:, 0], y=X_pca[:, 1], alpha=0.6)
            
        plt.title('PCA of RSNSD Flows')
        plt.xlabel('Principal Component 1')
        plt.ylabel('Principal Component 2')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "pca_visualization.png"), dpi=300)
        plt.close()
        
    def generate_correlation_matrix(self, df: pd.DataFrame):
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_cols) < 2:
            return
            
        corr = df[numeric_cols].corr()
        plt.figure(figsize=(12, 10))
        sns.heatmap(corr, cmap="coolwarm", center=0, annot=False)
        plt.title('Feature Correlation Matrix')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "correlation_matrix.png"), dpi=300)
        plt.close()
        
    def generate_class_distribution(self, df: pd.DataFrame, target_col: str = "service_class"):
        if target_col not in df.columns:
            return
            
        plt.figure(figsize=(8, 6))
        sns.countplot(data=df, x=target_col, hue=target_col, legend=False, palette="viridis")
        plt.title(f'Distribution of {target_col}')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, f"{target_col}_distribution.png"), dpi=300)
        plt.close()
