using Receiptly.Core.Services;
using Receiptly.Core.Interfaces;
using Receiptly.Infrastructure.Services;
using Receiptly.Infrastructure.Repositories;
using Receiptly.Infrastructure.Data;
using Receiptly.Infrastructure.Configuration;
using Microsoft.EntityFrameworkCore;
using Serilog;
using Polly;
using Polly.Extensions.Http;
using Amazon.SecretsManager;
using Amazon.SecretsManager.Model;
using System.Text.Json;

// Configure Serilog
Log.Logger = new LoggerConfiguration()
    .MinimumLevel.Information()
    .MinimumLevel.Override("Microsoft", Serilog.Events.LogEventLevel.Warning)
    .MinimumLevel.Override("System", Serilog.Events.LogEventLevel.Warning)
    .Enrich.FromLogContext()
    .WriteTo.Console()
    .WriteTo.File(
        path: "logs/receiptly-.log",
        rollingInterval: RollingInterval.Day,
        outputTemplate: "{Timestamp:yyyy-MM-dd HH:mm:ss.fff zzz} [{Level:u3}] {Message:lj}{NewLine}{Exception}")
    .CreateLogger();

try
{
    Log.Information("Starting Receiptly API");

    var builder = WebApplication.CreateBuilder(args);

    // Add Serilog
    builder.Host.UseSerilog();

    // Add CORS
    builder.Services.AddCors(options =>
    {
        options.AddPolicy("AllowAngularApp", policy =>
        {
            policy.WithOrigins(
                    "http://localhost:4200",  // Angular dev server
                    "http://localhost:8080",  // PWA production build
                    "http://localhost:8100",  // Ionic/Capacitor dev server
                    "http://192.168.100.240:8080", // PWA on network (mobile testing)
                    "capacitor://localhost",  // Capacitor iOS
                    "ionic://localhost",      // Capacitor Android
                    "http://localhost"        // Generic localhost
                )
                .AllowAnyMethod()
                .AllowAnyHeader()
                .AllowCredentials();
        });

        // Production CORS policy (configure with actual domain)
        options.AddPolicy("Production", policy =>
        {
            policy.WithOrigins(
                    builder.Configuration["CORS:AllowedOrigins"]?.Split(',') ?? Array.Empty<string>()
                )
                .AllowAnyMethod()
                .AllowAnyHeader()
                .AllowCredentials();
        });
    });

    // Add services to the container.
    builder.Services.AddControllers()
        .AddJsonOptions(options =>
        {
            // Prevent circular reference errors when serializing Receipt <-> Items
            options.JsonSerializerOptions.ReferenceHandler = System.Text.Json.Serialization.ReferenceHandler.IgnoreCycles;
            options.JsonSerializerOptions.DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull;
        });

    // Retrieve database credentials from AWS Secrets Manager
    string connectionString;
    try
    {
        var dbSecretId = builder.Configuration["AWS:DatabaseSecretId"] ?? "receiptly/database/credentials";
        var region = builder.Configuration["AWS:Region"] ?? "ap-southeast-1";

        Log.Information("Retrieving database credentials from Secrets Manager: {SecretId}", dbSecretId);

        using var secretsClient = new AmazonSecretsManagerClient(Amazon.RegionEndpoint.GetBySystemName(region));
        var dbSecretResponse = await secretsClient.GetSecretValueAsync(new GetSecretValueRequest
        {
            SecretId = dbSecretId
        });

        var dbConfig = JsonSerializer.Deserialize<DatabaseSecretsConfig>(dbSecretResponse.SecretString)
            ?? throw new InvalidOperationException("Failed to deserialize database credentials from Secrets Manager");

        connectionString = dbConfig.ToConnectionString();
        Log.Information("Successfully retrieved database credentials for: {Database}@{Host}", dbConfig.Database, dbConfig.Host);
    }
    catch (Exception ex)
    {
        Log.Error(ex, "Failed to retrieve database credentials from Secrets Manager. Falling back to configuration.");

        // Fallback to appsettings.json/user secrets for local development
        connectionString = builder.Configuration.GetConnectionString("DefaultConnection")
            ?? throw new InvalidOperationException("DefaultConnection not configured");
    }

    // Add PostgreSQL DbContext with retrieved connection string
    builder.Services.AddDbContext<ApplicationDbContext>(options =>
    {
        options.UseNpgsql(connectionString, npgsqlOptions =>
        {
            npgsqlOptions.EnableRetryOnFailure(
                maxRetryCount: 3,
                maxRetryDelay: TimeSpan.FromSeconds(5),
                errorCodesToAdd: null);
        });
        
        if (builder.Environment.IsDevelopment())
        {
            options.EnableSensitiveDataLogging();
            options.EnableDetailedErrors();
        }
    });

    // Retrieve S3 credentials from AWS Secrets Manager
    S3SecretsConfig s3Config;
    try
    {
        var secretId = builder.Configuration["AWS:S3SecretId"] ?? "receiptly/s3/credentials";
        var region = builder.Configuration["AWS:Region"] ?? "ap-southeast-1";
        
        Log.Information("Retrieving S3 credentials from Secrets Manager: {SecretId}", secretId);
        
        using var secretsClient = new AmazonSecretsManagerClient(Amazon.RegionEndpoint.GetBySystemName(region));
        var secretResponse = await secretsClient.GetSecretValueAsync(new GetSecretValueRequest
        {
            SecretId = secretId
        });
        
        s3Config = JsonSerializer.Deserialize<S3SecretsConfig>(secretResponse.SecretString)
            ?? throw new InvalidOperationException("Failed to deserialize S3 credentials from Secrets Manager");
        
        Log.Information("Successfully retrieved S3 credentials for bucket: {BucketName}", s3Config.BucketName);
    }
    catch (Exception ex)
    {
        Log.Error(ex, "Failed to retrieve S3 credentials from Secrets Manager. Falling back to configuration.");
        
        // Fallback to appsettings.json/user secrets for local development
        s3Config = new S3SecretsConfig
        {
            AwsAccessKeyId = builder.Configuration["AWS:AccessKeyId"] ?? throw new InvalidOperationException("AWS:AccessKeyId not configured"),
            AwsSecretAccessKey = builder.Configuration["AWS:SecretAccessKey"] ?? throw new InvalidOperationException("AWS:SecretAccessKey not configured"),
            BucketName = builder.Configuration["AWS:S3BucketName"] ?? throw new InvalidOperationException("AWS:S3BucketName not configured"),
            Region = builder.Configuration["AWS:Region"] ?? "ap-southeast-1"
        };
    }

    // Add S3 Storage Service with retrieved credentials
    builder.Services.AddSingleton(s3Config);
    builder.Services.AddSingleton<S3StorageService>();

    // Retrieve OCR service configuration from AWS Secrets Manager
    OcrServiceSecretsConfig ocrConfig;
    try
    {
        var secretId = builder.Configuration["AWS:OcrSecretId"] ?? "receiptly/ocr/service";
        var region = builder.Configuration["AWS:Region"] ?? "ap-southeast-1";
        
        Log.Information("Retrieving OCR service configuration from Secrets Manager: {SecretId}", secretId);
        
        using var secretsClient = new AmazonSecretsManagerClient(Amazon.RegionEndpoint.GetBySystemName(region));
        var secretResponse = await secretsClient.GetSecretValueAsync(new GetSecretValueRequest
        {
            SecretId = secretId
        });
        
        ocrConfig = JsonSerializer.Deserialize<OcrServiceSecretsConfig>(secretResponse.SecretString)
            ?? throw new InvalidOperationException("Failed to deserialize OCR service configuration from Secrets Manager");
        
        Log.Information("Successfully retrieved OCR service configuration: {BaseUrl}", ocrConfig.BaseUrl);
    }
    catch (Exception ex)
    {
        Log.Error(ex, "Failed to retrieve OCR service configuration from Secrets Manager. Falling back to configuration.");
        
        // Fallback to appsettings.json/user secrets for local development
        ocrConfig = new OcrServiceSecretsConfig
        {
            BaseUrl = builder.Configuration["PythonOcr:BaseUrl"] ?? "http://localhost:8000",
            HealthCheckUrl = builder.Configuration["PythonOcr:HealthCheckUrl"] ?? "http://localhost:8000/health"
        };
    }

    // Add OCR service configuration
    builder.Services.AddSingleton(ocrConfig);

    // Add File Validation Service
    builder.Services.AddScoped<FileValidationService>();
    
    // Add Image Hash Service
    builder.Services.AddScoped<IImageHashService, ImageHashService>();

    // Add Repository
    builder.Services.AddScoped<IReceiptRepository, ReceiptRepository>();

    // Add AutoMapper
    builder.Services.AddAutoMapper(typeof(Program).Assembly);

    // Add Python OCR Client with Polly retry policy
    builder.Services.AddHttpClient<PythonOcrClient>()
        .AddPolicyHandler(GetRetryPolicy());

    // Add Receipt Processing Service
    builder.Services.AddScoped<IReceiptProcessingService, ReceiptProcessingService>();

    // Learn more about configuring Swagger/OpenAPI at https://aka.ms/aspnetcore/swashbuckle
    builder.Services.AddEndpointsApiExplorer();
    builder.Services.AddSwaggerGen();

    var app = builder.Build();

    // Apply migrations automatically in development
    if (app.Environment.IsDevelopment())
    {
        using (var scope = app.Services.CreateScope())
        {
            var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
            try
            {
                Log.Information("Applying database migrations...");
                dbContext.Database.Migrate();
                Log.Information("Database migrations applied successfully");
            }
            catch (Exception ex)
            {
                Log.Warning(ex, "Could not apply database migrations. Database may not be available yet.");
            }
        }
    }

    // Configure the HTTP request pipeline.
    // Enable Swagger in non-production environments, or if explicitly enabled via configuration
    // TODO: Add authentication for Swagger in production
    if (!app.Environment.IsProduction() || app.Configuration.GetValue<bool>("Swagger:Enabled", false))
    {
        app.UseSwagger();
        app.UseSwaggerUI();
    }

    // Only use HTTPS redirection in production with proper certificates
    // app.UseHttpsRedirection();

    // Enable CORS
    if (app.Environment.IsDevelopment())
    {
        app.UseCors("AllowAngularApp");
    }
    else
    {
        app.UseCors("Production");
    }

    // Add Serilog request logging
    app.UseSerilogRequestLogging();

    // Health check endpoint
    app.MapGet("/health", () => Results.Ok(new
    {
        status = "healthy",
        service = "receiptly-api",
        timestamp = DateTime.UtcNow
    }));

    app.MapControllers();

    app.Run();
}
catch (Exception ex)
{
    Log.Fatal(ex, "Application terminated unexpectedly");
}
finally
{
    Log.CloseAndFlush();
}

// Polly retry policy for Python OCR client
static IAsyncPolicy<HttpResponseMessage> GetRetryPolicy()
{
    return HttpPolicyExtensions
        .HandleTransientHttpError() // Handles 5xx, 408, and network failures
        .OrResult(msg => msg.StatusCode == System.Net.HttpStatusCode.NotFound)
        .WaitAndRetryAsync(
            retryCount: 3,
            sleepDurationProvider: retryAttempt => TimeSpan.FromSeconds(Math.Pow(2, retryAttempt)),
            onRetry: (outcome, timespan, retryCount, context) =>
            {
                Log.Warning(
                    "Python OCR request failed. Retry {RetryCount}/3. Waiting {Delay}s before next attempt. Reason: {Reason}",
                    retryCount,
                    timespan.TotalSeconds,
                    outcome.Exception?.Message ?? outcome.Result?.StatusCode.ToString() ?? "Unknown");
            });
}
