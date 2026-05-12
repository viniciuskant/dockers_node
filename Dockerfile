FROM python:3.12-slim

WORKDIR /app

# Copy dependencies file and install packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your script into the container
COPY sim_node.py .

# Set the command to run your script with the arguments
CMD ["python", "sim_node.py", "-H", "192.168.18.110", "-s", "temperatura,umidade,pressao,co2,co,so2,no2", "-m", "-d", "1", "-i", "600"]
