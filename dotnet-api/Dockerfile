# Build stage
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# Copy solution and project files
COPY ["Receiptly.sln", "./"]
COPY ["src/Receiptly.API/Receiptly.API.csproj", "src/Receiptly.API/"]
COPY ["src/Receiptly.Core/Receiptly.Core.csproj", "src/Receiptly.Core/"]
COPY ["src/Receiptly.Domain/Receiptly.Domain.csproj", "src/Receiptly.Domain/"]
COPY ["src/Receiptly.Infrastructure/Receiptly.Infrastructure.csproj", "src/Receiptly.Infrastructure/"]

# Restore dependencies
RUN dotnet restore "src/Receiptly.API/Receiptly.API.csproj"

# Copy the rest of the source code
COPY . .

# Build the application
WORKDIR "/src/src/Receiptly.API"
RUN dotnet build "Receiptly.API.csproj" -c Release -o /app/build

# Publish stage
FROM build AS publish
RUN dotnet publish "Receiptly.API.csproj" -c Release -o /app/publish /p:UseAppHost=false

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app
EXPOSE 8080
EXPOSE 8081

COPY --from=publish /app/publish .

ENTRYPOINT ["dotnet", "Receiptly.API.dll"]
