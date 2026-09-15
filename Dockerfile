FROM amazonlinux:2023

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN dnf install -y python3.12 python3.12-pip gcc gcc-c++ make \
    && dnf clean all

# AL2023's default python3 is 3.9; the venv puts 3.12 first on PATH.
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY requirements.txt setup.py README.md ./
RUN pip install --upgrade pip setuptools wheel \
    && PIP_ONLY_BINARY=kiwisolver pip install "cppy>=1.1.0" "kiwisolver==1.4.5" \
    && pip install --prefer-binary -r requirements.txt

COPY src/ ./src/
COPY tests/test_files/ ./tests/test_files/
COPY api/ ./api/

RUN pip install -e .

EXPOSE 8000

# Run the API and the dispatcher side by side.
# If either process dies, wait -n returns, Docker restarts it.
CMD ["bash", "-c", "\
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 2 & \
    python -m api.dispatcher & \
    wait -n; \
    exit 1 \
"]
