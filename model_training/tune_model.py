import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import optuna

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class StockSequenceDataset(Dataset):
    def __init__(self, x_path, y_path):
        self.X = torch.tensor(np.load(x_path), dtype=torch.float32)
        self.y = torch.tensor(np.load(y_path), dtype=torch.float32)
        
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

class StockLSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, dropout_rate):
        super(StockLSTM, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True, dropout=dropout_rate)
        self.fc = nn.Linear(hidden_dim, 1)
        
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out.squeeze(-1)

def objective(trial):
    # 1. AI Suggests Hyperparameters
    hidden_dim = trial.suggest_categorical('hidden_dim', [32, 64, 128])
    num_layers = trial.suggest_int('num_layers', 1, 3)
    # Dropout is only applied if num_layers > 1 in PyTorch
    dropout_rate = trial.suggest_float('dropout', 0.1, 0.5) if num_layers > 1 else 0.0
    learning_rate = trial.suggest_float('lr', 1e-4, 1e-2, log=True)
    batch_size = trial.suggest_categorical('batch_size', [128, 256, 512])

    # 2. Load Data
    tensor_dir = 'model_training/data_tensors/'
    train_dataset = StockSequenceDataset(f'{tensor_dir}X_train.npy', f'{tensor_dir}y_train.npy')
    val_dataset = StockSequenceDataset(f'{tensor_dir}X_val.npy', f'{tensor_dir}y_val.npy')
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    # 3. Initialize Model
    model = StockLSTM(input_dim=47, hidden_dim=hidden_dim, num_layers=num_layers, dropout_rate=dropout_rate).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    epochs = 15 # Shorter runs for the search phase
    best_val_acc = 0.0
    
    # 4. Training Loop
    for epoch in range(epochs):
        model.train()
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
        # 5. Validation Loop
        model.eval()
        correct_directions = 0
        total_samples = 0
        
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                outputs = model(batch_X)
                
                direction_match = (outputs * batch_y) > 0
                correct_directions += direction_match.sum().item()
                total_samples += batch_y.size(0)
                
        val_directional_acc = (correct_directions / total_samples) * 100
        
        if val_directional_acc > best_val_acc:
            best_val_acc = val_directional_acc
            
        # Report back to Optuna to see if this trial is garbage and should be killed early
        trial.report(val_directional_acc, epoch)
        if trial.should_prune():
            raise optuna.exceptions.TrialPruned()

    # We want Optuna to maximize this number
    return best_val_acc

if __name__ == "__main__":
    print("Initializing Optuna Study...")
    # Maximize because we want the highest Directional Accuracy
    study = optuna.create_study(direction='maximize', study_name="LSTM_Tuning")
    
    # Run 20 different experiments. Your RTX 4050 should chew through this in a few minutes.
    study.optimize(objective, n_trials=20)
    
    print("\n======================================")
    print("🏆 BEST HYPERPARAMETERS FOUND 🏆")
    print("======================================")
    print(f"Best Validation Accuracy: {study.best_value:.2f}%")
    for key, value in study.best_trial.params.items():
        print(f"{key}: {value}")