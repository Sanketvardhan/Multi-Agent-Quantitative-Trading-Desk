import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# --- Dynamic Pathing ---
# This ensures it always looks in the exact folder where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TENSOR_DIR = os.path.join(BASE_DIR, 'data_tensors')
WEIGHTS_DIR = os.path.join(BASE_DIR, '..', 'weights') # Saves to Intraday_Engine/weights/
os.makedirs(WEIGHTS_DIR, exist_ok=True)

class StockSequenceDataset(Dataset):
    def __init__(self, x_path, y_path):
        self.X = torch.tensor(np.load(x_path), dtype=torch.float32)
        self.y = torch.tensor(np.load(y_path), dtype=torch.float32)
        
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

# ==========================================
# V4 COMPONENT: THE ATTENTION MECHANISM
# ==========================================
class Attention(nn.Module):
    def __init__(self, hidden_dim):
        super(Attention, self).__init__()
        self.attention = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, lstm_outputs):
        attn_weights = torch.softmax(self.attention(lstm_outputs), dim=1) 
        context_vector = torch.sum(attn_weights * lstm_outputs, dim=1) 
        return context_vector, attn_weights

# ==========================================
# THE INTRADAY ATTENTION ARCHITECTURE
# ==========================================
class StockCNNLSTMAttention(nn.Module):
    def __init__(self, input_dim, cnn_out_channels, kernel_size, hidden_dim, num_layers, dropout_rate):
        super(StockCNNLSTMAttention, self).__init__()
        pad = kernel_size // 2 
        
        self.conv1 = nn.Conv1d(in_channels=input_dim, out_channels=cnn_out_channels, kernel_size=kernel_size, padding=pad)
        self.relu = nn.ReLU()
        
        self.lstm = nn.LSTM(cnn_out_channels, hidden_dim, num_layers, batch_first=True, dropout=dropout_rate)
        
        self.attention = Attention(hidden_dim)
        self.fc = nn.Linear(hidden_dim, 1)
        
    def forward(self, x):
        x = x.permute(0, 2, 1) 
        x = self.conv1(x)
        x = self.relu(x)
        x = x.permute(0, 2, 1) 
        
        h0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(device)
        c0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(device)
        
        lstm_out, _ = self.lstm(x, (h0, c0))
        context_vector, _ = self.attention(lstm_out)
        
        out = self.fc(context_vector)
        return out.squeeze(-1)

def train_intraday_model():
    print(f"Deploying Intraday Attention Architecture to: {device}")
    
    # 1. Load Tensors dynamically
    print("Loading 26-Feature Intraday Tensors...")
    train_dataset = StockSequenceDataset(os.path.join(TENSOR_DIR, 'X_train.npy'), os.path.join(TENSOR_DIR, 'y_train.npy'))
    val_dataset = StockSequenceDataset(os.path.join(TENSOR_DIR, 'X_val.npy'), os.path.join(TENSOR_DIR, 'y_val.npy'))
    test_dataset = StockSequenceDataset(os.path.join(TENSOR_DIR, 'X_test.npy'), os.path.join(TENSOR_DIR, 'y_test.npy'))
    
    batch_size = 512
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    # 2. Inject Optuna's Winning Parameters
    model = StockCNNLSTMAttention(
        input_dim=26, 
        cnn_out_channels=128, 
        kernel_size=5,
        hidden_dim=128, 
        num_layers=1, 
        dropout_rate=0.0 # Optuna sets 0.0 dropout for 1-layer LSTMs
    ).to(device)
    
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.00028163919791980097)
    
    epochs = 30
    best_val_acc = 0.0
    model_save_path = os.path.join(WEIGHTS_DIR, 'best_intraday_attention.pth')
    
    print("\nTraining Final Intraday Attention Model...")
    for epoch in range(epochs):
        model.train()
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
        # Validation Eval
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
        print(f"Epoch [{epoch+1}/{epochs}] | Val Dir Acc: {val_acc:.2f}%")
        
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), model_save_path)
            
    print("\n--- FINAL UNSEEN TEST SET EVALUATION ---")
    model.load_state_dict(torch.load(model_save_path, weights_only=True))
    model.eval()
    
    correct_directions = 0
    total_samples = 0
    with torch.no_grad():
        for batch_X, batch_y in test_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            outputs = model(batch_X)
            direction_match = (outputs * batch_y) > 0
            correct_directions += direction_match.sum().item()
            total_samples += batch_y.size(0)
            
    test_acc = (correct_directions / total_samples) * 100
    print(f"Unseen Intraday Test Set Directional Accuracy: {test_acc:.2f}%")
    print(f"Final Intraday model frozen and saved to: {model_save_path}")

if __name__ == "__main__":
    train_intraday_model()