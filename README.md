# Step 1: Create an Azure Container Registry

az acr create -n melonopsmainregistry --resource-group melonops --sku Standard

# Step 2: Create the Container App Environment

az containerapp env create -n melonopsmainenv -g melonops --location eastus

# Step 3: Create the Container App with a system-assigned identity

az containerapp create --name melonops-backend --resource-group melonops --environment melonopsmainenv --image mcr.microsoft.com/azuredocs/containerapps-helloworld:latest --ingress external --cpu 0.5 --memory 1.0Gi --system-assigned

# Step 4: Get the ACR resource ID

$acrId = az acr show -n melonopsmainregistry -g melonops --query id -o tsv

# Step 5: Get the Container App's managed identity principal ID

$principalId = az containerapp show -n melonops-backend -g melonops --query identity.principalId -o tsv

# Step 6: Assign AcrPull role to the Container App's identity

az role assignment create --assignee $principalId --role AcrPull --scope $acrId

# Step 7: Link the ACR to the Container App using system-assigned identity

az containerapp registry set --name melonops-backend --resource-group melonops --server melonopsmainregistry.azurecr.io --identity system
