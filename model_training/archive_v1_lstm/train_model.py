import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torch.utils.tensorboard import SummaryWriter
import numpy as np

# Set device to GPU if available on your TUF laptop, otherwise CPU
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

# 1. Custom PyTorch Dataset
class StockSequenceDataset(Dataset):
    def __init__(self, x_path, y_path):
        # Load the saved .npy files
        self.X = torch.tensor(np.load(x_path), dtype=torch.float32)
        self.y = torch.tensor(np.load(y_path), dtype=torch.float32)
        
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

# 2. LSTM Neural Network Architecture
class StockLSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, output_dim=1):
        super(StockLSTM, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # LSTM Layer (batch_first=True matches our (Batch, Time, Features) data)
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True, dropout=0.2)
        
        # Fully Connected Output Layer
        self.fc = nn.Linear(hidden_dim, output_dim)
        
    def forward(self, x):
        # Initialize hidden and cell states with zeros
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(device)
        
        # Forward propagate through LSTM
        out, _ = self.lstm(x, (h0, c0))
        
        # Decode the hidden state of the very last time step (Day 30)
        out = self.fc(out[:, -1, :])
        return out.squeeze(-1) # Squeeze to shape (Batch,) to match target y

# 3. Main Training Routine
def train_pipeline(resume_from_checkpoint=None):
    # Paths to tensors
    tensor_dir = 'model_training/data_tensors/'
    checkpoint_dir = 'model_training/checkpoints/'
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    print("Loading data into PyTorch DataLoaders...")
    train_dataset = StockSequenceDataset(f'{tensor_dir}X_train.npy', f'{tensor_dir}y_train.npy')
    val_dataset = StockSequenceDataset(f'{tensor_dir}X_val.npy', f'{tensor_dir}y_val.npy')
    
    train_loader = DataLoader(train_dataset, batch_size=256, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=256, shuffle=False)
    
    # Model Parameters
    input_dim = 47   # Your 47 engineered features
    hidden_dim = 64  # Hidden units inside LSTM
    num_layers = 2   # Stacked LSTMs
    epochs = 30
    
    model = StockLSTM(input_dim, hidden_dim, num_layers).to(device)
    criterion = nn.MSELoss() # Predicting return directly uses Mean Squared Error
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    start_epoch = 0
    
    # --- Checkpoint Loading Logic ---
    if resume_from_checkpoint and os.path.exists(resume_from_checkpoint):
        print(f"Resuming training from checkpoint: {resume_from_checkpoint}")
        checkpoint = torch.load(resume_from_checkpoint, map_location=device)
        model.load_state_dict(checkpoint['model_state'])
        optimizer.load_state_dict(checkpoint['optimizer_state'])
        start_epoch = checkpoint['epoch'] + 1
        print(f"Successfully loaded. Starting back up at Epoch {start_epoch}")
        
    # Initialize TensorBoard Writer
    writer = SummaryWriter('model_training/runs/lstm_experiment_1')
    
    print("Beginning Training Loop...")
    for epoch in range(start_epoch, epochs):
        model.train()
        train_loss = 0.0
        
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            
            # Forward pass
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            
            # Backward pass and optimization
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item() * batch_X.size(0)
            
        avg_train_loss = train_loss / len(train_loader.dataset)
        
        # --- Validation Loop ---
        model.eval()
        val_loss = 0.0
        correct_directions = 0
        total_samples = 0
        
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item() * batch_X.size(0)
                
                # Directional Accuracy calculation
                direction_match = (outputs * batch_y) > 0
                correct_directions += direction_match.sum().item()
                total_samples += batch_y.size(0)
                
        avg_val_loss = val_loss / len(val_loader.dataset)
        val_directional_acc = (correct_directions / total_samples) * 100
        
        print(f"Epoch [{epoch+1}/{epochs}] | Train Loss: {avg_train_loss:.6f} | Val Loss: {avg_val_loss:.6f} | Val Dir Acc: {val_directional_acc:.2f}%")
        
        # Log metrics to TensorBoard
        writer.add_scalar('Loss/Train', avg_train_loss, epoch)
        writer.add_scalar('Loss/Validation', avg_val_loss, epoch)
        writer.add_scalar('Accuracy/Val_Directional', val_directional_acc, epoch)
        
        # --- Save Checkpoint ---
        checkpoint_path = os.path.join(checkpoint_dir, 'latest_checkpoint.pth')
        torch.save({
            'epoch': epoch,
            'model_state': model.state_dict(),
            'optimizer_state': optimizer.state_dict(),
        }, checkpoint_path)
        
    writer.close()
    print("Training Complete!")

if __name__ == "__main__":
    # To start fresh, leave this as None. 
    # To resume later, change it to 'model_training/checkpoints/latest_checkpoint.pth'
    train_pipeline(resume_from_checkpoint=None)