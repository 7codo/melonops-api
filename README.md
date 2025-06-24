az acr create -n melonopsmainregistry --resource-group melonops --sku Standard
az containerapp env create -n melonopsmainenv -g melonops --location eastus

az containerapp create --name melonops-backend --resource-group melonops --environment melonopsmainenv --image mcr.microsoft.com/azuredocs/containerapps-helloworld:latest --ingress external --cpu 0.5 --memory 1Gi --system-assigned

$acrId = az acr show -n melonopsmainregistry -g melonops --query id -o tsv

$principalId = az containerapp show -n melonops-backend -g melonops --query identity.principalId -o tsv

az role assignment create --assignee $principalId --role AcrPull --scope $acrId

az containerapp registry set --name melonops-backend --resource-group melonops --server melonopsmainregistry.azurecr.io --identity system
