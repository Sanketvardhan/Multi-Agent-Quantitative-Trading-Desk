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

# ==========================================
# NEW V4 COMPONENT: THE ATTENTION MECHANISM
# ==========================================
class Attention(nn.Module):
    def __init__(self, hidden_dim):
        super(Attention, self).__init__()
        self.attention = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, lstm_outputs):
        # lstm_outputs shape: (batch_size, 30_days, hidden_dim)
        
        # Calculate relevance score for each day
        attn_weights = torch.softmax(self.attention(lstm_outputs), dim=1) 
        
        # Multiply the day's data by its relevance score
        context_vector = torch.sum(attn_weights * lstm_outputs, dim=1) 
        
        return context_vector, attn_weights

# ==========================================
# THE V4 ARCHITECTURE
# ==========================================
class StockCNNLSTMAttention(nn.Module):
    def __init__(self, input_dim, cnn_out_channels, kernel_size, hidden_dim, num_layers, dropout_rate):
        super(StockCNNLSTMAttention, self).__init__()
        pad = kernel_size // 2 
        
        self.conv1 = nn.Conv1d(in_channels=input_dim, out_channels=cnn_out_channels, kernel_size=kernel_size, padding=pad)
        self.relu = nn.ReLU()
        
        self.lstm = nn.LSTM(cnn_out_channels, hidden_dim, num_layers, batch_first=True, dropout=dropout_rate)
        
        # Inject the Attention Layer
        self.attention = Attention(hidden_dim)
        
        self.fc = nn.Linear(hidden_dim, 1)
        
    def forward(self, x):
        x = x.permute(0, 2, 1) 
        x = self.conv1(x)
        x = self.relu(x)
        x = x.permute(0, 2, 1) 
        
        h0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(device)
        c0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(device)
        
        # Get output for ALL 30 days, not just the last one
        lstm_out, _ = self.lstm(x, (h0, c0))
        
        # Pass all 30 days to Attention Memory Manager
        context_vector, _ = self.attention(lstm_out)
        
        out = self.fc(context_vector)
        return out.squeeze(-1)

def objective(trial):
    # Search Space
    cnn_channels = trial.suggest_categorical('cnn_channels', [64, 128])
    kernel_size = 5 
    hidden_dim = trial.suggest_categorical('hidden_dim', [64, 128])
    num_layers = trial.suggest_int('num_layers', 1, 2)
    dropout_rate = trial.suggest_float('dropout', 0.2, 0.5) if num_layers > 1 else 0.0
    learning_rate = trial.suggest_float('lr', 1e-4, 2e-3, log=True)
    batch_size = 512

    # Load Tensors
    tensor_dir = 'model_training/data_tensors/'
    train_dataset = StockSequenceDataset(f'{tensor_dir}X_train.npy', f'{tensor_dir}y_train.npy')
    val_dataset = StockSequenceDataset(f'{tensor_dir}X_val.npy', f'{tensor_dir}y_val.npy')
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    # Init V4 Model
    model = StockCNNLSTMAttention(
        input_dim=52, 
        cnn_out_channels=cnn_channels, 
        kernel_size=kernel_size,
        hidden_dim=hidden_dim, 
        num_layers=num_layers, 
        dropout_rate=dropout_rate
    ).to(device)
    
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    epochs = 12 
    best_val_acc = 0.0
    
    for epoch in range(epochs):
        model.train()
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
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
                
        val_acc = (correct_directions / total_samples) * 100
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            
        trial.report(val_acc, epoch)
        if trial.should_prune():
            raise optuna.exceptions.TrialPruned()

    return best_val_acc

if __name__ == "__main__":
    print("Initializing V4 ATTENTION Optuna Study...")
    study = optuna.create_study(direction='maximize', study_name="Attention_Tuning")
    study.optimize(objective, n_trials=20) 
    
    print("\n======================================")
    print("🏆 BEST V4 ATTENTION PARAMETERS 🏆")
    print("======================================")
    print(f"Best Validation Accuracy: {study.best_value:.2f}%")
    for key, value in study.best_trial.params.items():
        print(f"{key}: {value}")