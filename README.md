# RAG Q&A Application

A Retrieval Augmented Generation (RAG) application that lets you ask questions about your PDF documents. Upload your PDFs, index them into Pinecone, and query them using a FastAPI backend powered by Groq's Llama3 model.

**Tech Stack:**
- Embeddings: `sentence-transformers/multi-qa-MiniLM-L6-cos-v1` (runs locally)
- Vector Database: Pinecone
- LLM: Llama 3.3 70B via Groq API
- Framework: FastAPI

---

## How It Works

```
Step 1 — Run once on your laptop:

  Your PDFs
      │
      ▼
  indexing.py
  (chunks PDFs, creates embeddings)
      │
      ▼
  Pinecone (cloud vector database)
  stores your document chunks permanently


Step 2 — Runs continuously on EC2 / locally:

  User sends question
        │
        ▼
  FastAPI (EC2 / local)
  converts question to vector
        │
        ▼
  Pinecone
  finds most relevant chunks
        │
        ▼
  Groq LLM (Llama 3.3 70B)
  reads chunks + answers question
        │
        ▼
  Answer returned to user
```

---

## Part 1 — Get Your API Keys

### Pinecone API Key
1. Go to [app.pinecone.io](https://app.pinecone.io) and create a free account
2. On the left sidebar click **API Keys**
3. Click **Create API Key**
4. Copy and save the key somewhere safe

### Groq API Key
1. Go to [console.groq.com](https://console.groq.com) and create a free account
2. On the left sidebar click **API Keys**
3. Click **Create API Key**
4. Copy and save the key somewhere safe

---

## Part 2 — Index Your PDFs

This step runs on your **local machine** and uploads your PDF content into Pinecone. This is a one-time step per document set.

### Prerequisites
- Python 3.10 or above installed
- Your PDF files ready in a folder

### Steps

**1. Clone the repository:**
```bash
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name
```

**2. Install dependencies:**
```bash
pip install -r requirements.txt
```

**3. Add your API keys to the `.env` file:**

Open the `.env` file and fill in your keys:
```
PINECONE_API_KEY=your_pinecone_key_here
GROQ_API_KEY=your_groq_key_here
```

**4. Run the indexing script:**
```bash
python indexing.py
```

You will be prompted for two inputs:
```
Enter folder path: C:\Users\You\Documents\pdfs
Enter index name (lowercase, hyphens only): budget-2023
```

- **Folder path** — the folder on your machine that contains your PDF files
- **Index name** — a name for this document set in Pinecone (use lowercase letters and hyphens only, e.g. `budget-2023`, `company-docs`)

You will see output like:
```
Found 1 PDF(s): ['budget_speech.pdf']
Loading PDFs...
Loaded 58 pages
Chunking...
Created 312 chunks
Loading embedding model...
Creating index 'budget-2023'...
Index 'budget-2023' is ready.
Uploading vectors to 'budget-2023'...
Done. Index 'budget-2023' is ready to query.
```

> **Adding new documents later:** If you add new PDFs to the same folder and run `indexing.py` again with the same index name, it will skip index creation and only upload the new chunks. You do not need to delete the existing index.

---

## Part 3 — Run the Application

Choose one of the two options below depending on where you are running the app.

---

### Option A — Running on AWS EC2 (Recommended for Production)

#### Step 1 — Launch EC2 Instance

1. Go to [AWS Console](https://console.aws.amazon.com) → **EC2** → **Launch Instance**
2. Fill in the following:
   ```
   Name:          rag-app-server
   AMI:           Amazon Linux 2023 (free tier eligible)
   Instance type: t2.micro (free tier eligible)
   Key pair:      Create new → Name: rag-app-key → RSA → .pem format
                  Download and save safely — cannot be downloaded again
   Storage:       20 GB
   ```
3. Under **Network settings** check all three:
   - ✅ Allow SSH traffic from: My IP
   - ✅ Allow HTTP traffic from the internet
   - ✅ Allow HTTPS traffic from the internet
4. Click **Launch Instance**

#### Step 2 — Open Port 8080

1. Go to **EC2** → click your instance → **Security** tab at the bottom
2. Click the **Security Group** link
3. Click **Edit inbound rules** → **Add rule**
   ```
   Type:   Custom TCP
   Port:   8080
   Source: 0.0.0.0/0
   ```
4. Click **Save rules**

#### Step 3 — Store API Keys in AWS Parameter Store

This stores your keys securely in AWS so the app can fetch them automatically without any `.env` file on the server.

> **Important:** Make sure you are in the **ap-south-1 (Mumbai)** region in AWS Console before creating parameters. Check the top right corner of the AWS Console.

1. Go to AWS Console → search **Systems Manager** → **Parameter Store** → **Create Parameter**

   **First parameter:**
   ```
   Name:  /rag-app/PINECONE_API_KEY
   Tier:  Standard
   Type:  SecureString
   Value: your_actual_pinecone_key
   ```
   Click **Create Parameter**

   **Second parameter:**
   ```
   Name:  /rag-app/GROQ_API_KEY
   Tier:  Standard
   Type:  SecureString
   Value: your_actual_groq_key
   ```
   Click **Create Parameter**

#### Step 4 — Create IAM Role for EC2

This gives your EC2 instance permission to read from Parameter Store automatically.

1. Go to AWS Console → **IAM** → **Roles** → **Create Role**
2. Fill in:
   ```
   Trusted entity type: AWS Service
   Use case:            EC2
   ```
   Click **Next**
3. Search for and select: `AmazonSSMReadOnlyAccess`
   Click **Next**
4. Role name: `rag-app-ec2-role`
   Click **Create Role**

#### Step 5 — Attach IAM Role to EC2

1. Go to **EC2** → click your instance
2. Click **Actions** (top right) → **Security** → **Modify IAM Role**
3. Select `rag-app-ec2-role`
4. Click **Update IAM Role**

#### Step 6 — SSH Into EC2

```bash
# Mac / Linux
chmod 400 rag-app-key.pem
ssh -i rag-app-key.pem ec2-user@YOUR_EC2_PUBLIC_IP

# Windows PowerShell
ssh -i rag-app-key.pem ec2-user@YOUR_EC2_PUBLIC_IP
```

Replace `YOUR_EC2_PUBLIC_IP` with the public IP shown in your EC2 instance details.

#### Step 7 — Add Swap Memory

t2.micro has only 1GB RAM. Adding swap prevents the app from running out of memory when loading the embedding model.

Run these commands one by one inside EC2:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Verify swap was added:
```bash
free -h
# Should show 2GB under Swap
```

#### Step 8 — Install Docker

```bash
sudo yum update -y
sudo yum install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user
```

Log out and back in for the group change to take effect:
```bash
exit
ssh -i rag-app-key.pem ec2-user@YOUR_EC2_PUBLIC_IP
```

Verify Docker is working:
```bash
docker --version
```

#### Step 9 — Pull and Run the Container

```bash
# Pull the image
docker pull vishnuprasad54190/my_rag_app

# Run the container
docker run -d \
  -p 8080:8080 \
  --restart unless-stopped \
  --name rag-container \
  vishnuprasad54190/my_rag_app
```

No API keys needed here — the app automatically fetches them from AWS Parameter Store using the IAM role.

#### Step 10 — Verify It Is Running

```bash
docker logs -f rag-container
```

You should see:
```
Keys not found in .env, fetching from AWS Parameter Store...
Secrets loaded from AWS Parameter Store.
Loading embedding models...
App ready!
INFO: Uvicorn running on http://0.0.0.0:8080
```

---

### Option B — Running Locally or on Any Other Server (Without EC2)

You will need Docker installed on your machine. Download Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop).

**Pull the image:**
```bash
docker pull vishnuprasad54190/my_rag_app
```

**Run the container with your API keys:**
```bash
docker run -d \
  -p 8080:8080 \
  --name rag-container \
  -e PINECONE_API_KEY=your_pinecone_key \
  -e GROQ_API_KEY=your_groq_key \
  vishnuprasad54190/my_rag_app
```

**Verify it is running:**
```bash
docker logs rag-container
```

You should see:
```
Secrets loaded from environment variables.
Loading embedding models...
App ready!
INFO: Uvicorn running on http://0.0.0.0:8080
```

---

## Part 4 — Using the API

Once the container is running, open your browser and go to:

```
http://YOUR_EC2_PUBLIC_IP:8080/docs    ← if running on EC2
http://localhost:8080/docs             ← if running locally
```

This opens the interactive API documentation where you can test all endpoints directly from the browser.

### Available Endpoints

**GET `/health`** — Check if the app is running
```bash
curl http://YOUR_HOST:8080/health
# {"status":"ok"}
```

**GET `/indexes`** — List all available Pinecone indexes
```bash
curl http://YOUR_HOST:8080/indexes
# {"indexes":["budget-2023"]}
```

**POST `/ask`** — Ask a question about your documents
```bash
curl -X POST http://YOUR_HOST:8080/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the agriculture credit target?",
    "index_name": "budget-2023"
  }'
```

Response:
```json
{
  "answer": "The agriculture credit target will be increased to ₹20 lakh crore...",
  "index_used": "budget-2023"
}
```

---

## Troubleshooting

**Container exits immediately:**
```bash
docker logs rag-container
# Read the error message
```

**`NoCredentialsError` on EC2:**
- Check that the IAM role `rag-app-ec2-role` is attached to your EC2 instance (Step 5)

**`ParameterNotFound` error:**
- Check that your parameter names in AWS Parameter Store exactly match `/rag-app/PINECONE_API_KEY` and `/rag-app/GROQ_API_KEY`
- Check that you created them in the correct region (ap-south-1)

**Index not found:**
- Run `indexing.py` first (Part 2) before querying
- Call `GET /indexes` to see what indexes are available

**Out of memory on EC2:**
- Make sure you added swap memory in Step 7
