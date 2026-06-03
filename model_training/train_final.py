import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np

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

def train_and_save_final():
    print(f"Deploying to: {device}")
    
    # 1. Load Data
    tensor_dir = 'model_training/data_tensors/'
    train_dataset = StockSequenceDataset(f'{tensor_dir}X_train.npy', f'{tensor_dir}y_train.npy')
    val_dataset = StockSequenceDataset(f'{tensor_dir}X_val.npy', f'{tensor_dir}y_val.npy')
    test_dataset = StockSequenceDataset(f'{tensor_dir}X_test.npy', f'{tensor_dir}y_test.npy')
    
    # Using the winning batch_size
    batch_size = 128
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    # 2. Inject Optuna's Winning Parameters
    model = StockLSTM(
        input_dim=47, 
        hidden_dim=64, 
        num_layers=3, 
        dropout_rate=0.4804900011565837
    ).to(device)
    
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.00024710002476153266)
    
    epochs = 30
    best_val_acc = 0.0
    
    print("Training Final Model...")
    for epoch in range(epochs):
        model.train()
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
        # Validation evaluation
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
        
        # Save the absolute best weights
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            os.makedirs('weights', exist_ok=True)
            torch.save(model.state_dict(), 'weights/best_lstm_v1.pth')
            
    print("\n--- FINAL TEST SET EVALUATION ---")
    # Load the best weights we just saved
    model.load_state_dict(torch.load('weights/best_lstm_v1.pth'))
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
    print(f"Unseen 2024 Test Set Directional Accuracy: {test_acc:.2f}%")
    print("Model architecture frozen and saved to /weights/best_lstm_v1.pth")

if __name__ == "__main__":
    train_and_save_final()