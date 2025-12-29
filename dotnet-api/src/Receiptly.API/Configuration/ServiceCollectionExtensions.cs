using Amazon.SecretsManager;
using Amazon.SecretsManager.Model;
using Microsoft.EntityFrameworkCore;
using Polly;
using Polly.Extensions.Http;
using Receiptly.Core.Interfaces;
using Receiptly.Core.Services;
using Receiptly.Infrastructure.Configuration;
using Receiptly.Infrastructure.Data;
using Receiptly.Infrastructure.Repositories;
using Receiptly.Infrastructure.Services;
using Serilog;
using System.Text.Json;

namespace Receiptly.API.Configuration;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddCorsConfiguration(this IServiceCollection services, IConfiguration configuration)
    {
        services.AddCors(options =>
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
                        "http://localhost",        // Generic localhost
                        "https://d3c72tjxsq9089.cloudfront.net",
                        "https://cheap-sy.com",    // Production domain
                        "https://api.cheap-sy.com", // API subdomain
                        "https://ocr.cheap-sy.com", // OCR subdomain
                        "https://llm.cheap-sy.com"  // LLM subdomain
                    )
                    .AllowAnyMethod()
                    .AllowAnyHeader()
                    .AllowCredentials();
            });

            // Production CORS policy
            options.AddPolicy("Production", policy =>
            {
                policy.WithOrigins(
                        configuration["CORS:AllowedOrigins"]?.Split(',') ?? Array.Empty<string>()
                    )
                    .AllowAnyMethod()
                    .AllowAnyHeader()
                    .AllowCredentials();
            });
        });

        return services;
    }

    public static async Task<IServiceCollection> AddDatabaseConfiguration(
        this IServiceCollection services,
        IConfiguration configuration,
        IWebHostEnvironment environment)
    {
        string connectionString;
        
        try
        {
            var dbSecretId = configuration["AWS:DatabaseSecretId"] ?? "receiptly/database/credentials";
            var region = configuration["AWS:Region"] ?? "ap-southeast-1";

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
            connectionString = configuration.GetConnectionString("DefaultConnection")
                ?? throw new InvalidOperationException("DefaultConnection not configured");
        }

        services.AddDbContext<ApplicationDbContext>(options =>
        {
            options.UseNpgsql(connectionString, npgsqlOptions =>
            {
                npgsqlOptions.UseVector();
                npgsqlOptions.EnableRetryOnFailure(
                    maxRetryCount: 3,
                    maxRetryDelay: TimeSpan.FromSeconds(5),
                    errorCodesToAdd: null);
            });

            if (environment.IsDevelopment())
            {
                options.EnableSensitiveDataLogging();
                options.EnableDetailedErrors();
            }
        });

        return services;
    }

    public static async Task<IServiceCollection> AddAwsServices(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        // Retrieve S3 credentials from AWS Secrets Manager
        S3SecretsConfig s3Config;
        try
        {
            var secretId = configuration["AWS:S3SecretId"] ?? "receiptly/s3/credentials";
            var region = configuration["AWS:Region"] ?? "ap-southeast-1";

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
                AwsAccessKeyId = configuration["AWS:AccessKeyId"] ?? throw new InvalidOperationException("AWS:AccessKeyId not configured"),
                AwsSecretAccessKey = configuration["AWS:SecretAccessKey"] ?? throw new InvalidOperationException("AWS:SecretAccessKey not configured"),
                BucketName = configuration["AWS:S3BucketName"] ?? throw new InvalidOperationException("AWS:S3BucketName not configured"),
                Region = configuration["AWS:Region"] ?? "ap-southeast-1"
            };
        }

        services.AddSingleton(s3Config);
        services.AddSingleton<S3StorageService>();

        return services;
    }

    public static async Task<IServiceCollection> AddOcrService(
        this IServiceCollection services,
        IConfiguration configuration,
        IWebHostEnvironment environment)
    {
        OcrServiceSecretsConfig ocrConfig;

        // In Development mode, prioritize appsettings configuration
        if (environment.IsDevelopment())
        {
            var configuredBaseUrl = configuration["PythonOcr:BaseUrl"];
            
            if (!string.IsNullOrEmpty(configuredBaseUrl))
            {
                Log.Information("Development mode: Using OCR service URL from configuration: {BaseUrl}", configuredBaseUrl);
                
                ocrConfig = new OcrServiceSecretsConfig
                {
                    BaseUrl = configuredBaseUrl,
                    HealthCheckUrl = configuration["PythonOcr:HealthCheckUrl"] ?? $"{configuredBaseUrl}/health"
                };
                
                services.AddSingleton(ocrConfig);
                services.AddHttpClient<PythonOcrClient>()
                    .ConfigureHttpClient(client =>
                    {
                        // Increase timeout for OCR processing from mobile devices
                        // Mobile uploads can be large (5-10MB) and OCR involves:
                        // 1. S3 upload, 2. Image download, 3. Cropping, 4. Tesseract, 5. Azure processing
                        client.Timeout = TimeSpan.FromMinutes(5); // 300 seconds
                    })
                    .AddPolicyHandler(GetRetryPolicy());

                return services;
            }
        }

        // Retrieve OCR service configuration from AWS Secrets Manager (Production)
        try
        {
            var secretId = configuration["AWS:OcrSecretId"] ?? "receiptly/ocr/service";
            var region = configuration["AWS:Region"] ?? "ap-southeast-1";

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
                BaseUrl = configuration["PythonOcr:BaseUrl"] ?? "http://localhost:8000",
                HealthCheckUrl = configuration["PythonOcr:HealthCheckUrl"] ?? "http://localhost:8000/health"
            };
        }

        services.AddSingleton(ocrConfig);
        services.AddHttpClient<PythonOcrClient>()
            .ConfigureHttpClient(client =>
            {
                // Increase timeout for OCR processing from mobile devices
                // Mobile uploads can be large (5-10MB) and OCR involves:
                // 1. S3 upload, 2. Image download, 3. Cropping, 4. Tesseract, 5. Azure processing
                client.Timeout = TimeSpan.FromMinutes(5); // 300 seconds
            })
            .AddPolicyHandler(GetRetryPolicy());

        return services;
    }

    public static IServiceCollection AddApplicationServices(this IServiceCollection services)
    {
        // File services
        services.AddScoped<FileValidationService>();
        services.AddScoped<IImageHashService, ImageHashService>();

        // Repository
        services.AddScoped<IReceiptRepository, ReceiptRepository>();

        // Feedback repositories
        services.AddScoped<IUserCorrectionRepository, UserCorrectionRepository>();
        services.AddScoped<IIssueReportRepository, IssueReportRepository>();
        services.AddScoped<IUserDebugSessionRepository, UserDebugSessionRepository>();

        // Business services
        services.AddScoped<IReceiptProcessingService, ReceiptProcessingService>();
        services.AddScoped<IPurchaseAnalyticsService, PurchaseAnalyticsService>();
        services.AddScoped<IFeedbackService, FeedbackService>();
        
        // Points and Rewards services
        services.AddScoped<IPointsService, PointsService>();
        
        // Receipt services (with automatic correction application)
        services.AddScoped<IReceiptCorrectionService, ReceiptCorrectionService>();
        services.AddScoped<IReceiptService, ReceiptService>();

        // Gold layer service (append-only analytics)
        services.AddScoped<IGoldLayerService, GoldLayerService>();

        // LLM Services - configuration added via AddLlmService method
        services.AddScoped<CanonicalizationService>();

        // AutoMapper
        services.AddAutoMapper(typeof(Program).Assembly);

        return services;
    }

    public static async Task<IServiceCollection> AddLlmService(
        this IServiceCollection services,
        IConfiguration configuration,
        IWebHostEnvironment environment)
    {
        LlmServiceSecretsConfig llmConfig;

        // In Development mode, prioritize appsettings configuration
        if (environment.IsDevelopment())
        {
            var configuredBaseUrl = configuration["LlmService:BaseUrl"];
            
            if (!string.IsNullOrEmpty(configuredBaseUrl))
            {
                Log.Information("Development mode: Using LLM service URL from configuration: {BaseUrl}", configuredBaseUrl);
                
                llmConfig = new LlmServiceSecretsConfig
                {
                    BaseUrl = configuredBaseUrl,
                    HealthCheckUrl = configuration["LlmService:HealthCheckUrl"] ?? $"{configuredBaseUrl}/health"
                };
                
                services.AddSingleton(llmConfig);
                services.AddHttpClient<LlmServiceClient>()
                    .ConfigureHttpClient(client =>
                    {
                        client.Timeout = TimeSpan.FromMinutes(2); // LLM processing timeout
                    })
                    .AddPolicyHandler(GetRetryPolicy());

                return services;
            }
        }

        // Retrieve LLM service configuration from AWS Secrets Manager (Production)
        try
        {
            var secretId = configuration["AWS:LlmSecretId"] ?? "receiptly/llm/service";
            var region = configuration["AWS:Region"] ?? "ap-southeast-1";

            Log.Information("Retrieving LLM service configuration from Secrets Manager: {SecretId}", secretId);

            using var secretsClient = new AmazonSecretsManagerClient(Amazon.RegionEndpoint.GetBySystemName(region));
            var secretResponse = await secretsClient.GetSecretValueAsync(new GetSecretValueRequest
            {
                SecretId = secretId
            });

            llmConfig = JsonSerializer.Deserialize<LlmServiceSecretsConfig>(secretResponse.SecretString)
                ?? throw new InvalidOperationException("Failed to deserialize LLM service configuration from Secrets Manager");

            Log.Information("Successfully retrieved LLM service configuration: {BaseUrl}", llmConfig.BaseUrl);
        }
        catch (Exception ex)
        {
            Log.Error(ex, "Failed to retrieve LLM service configuration from Secrets Manager. Falling back to configuration.");

            // Fallback to appsettings.json/user secrets for local development
            llmConfig = new LlmServiceSecretsConfig
            {
                BaseUrl = configuration["LlmService:BaseUrl"] ?? "http://localhost:8500",
                HealthCheckUrl = configuration["LlmService:HealthCheckUrl"] ?? "http://localhost:8500/health"
            };
        }

        services.AddSingleton(llmConfig);
        services.AddHttpClient<LlmServiceClient>()
            .ConfigureHttpClient(client =>
            {
                client.Timeout = TimeSpan.FromMinutes(2); // LLM processing timeout
            })
            .AddPolicyHandler(GetRetryPolicy());

        return services;
    }

    public static async Task<IServiceCollection> AddGooglePlacesService(
        this IServiceCollection services,
        IConfiguration configuration,
        IWebHostEnvironment environment)
    {
        GooglePlacesSecretsConfig googleConfig;

        // In Development mode, prioritize appsettings configuration
        if (environment.IsDevelopment())
        {
            var configuredApiKey = configuration["GooglePlaces:ApiKey"];
            
            if (!string.IsNullOrEmpty(configuredApiKey))
            {
                Log.Information("Development mode: Using Google Places API key from configuration");
                
                googleConfig = new GooglePlacesSecretsConfig
                {
                    ApiKey = configuredApiKey,
                    Enabled = bool.Parse(configuration["GooglePlaces:Enabled"] ?? "true")
                };
                
                services.AddSingleton(googleConfig);
                services.AddHttpClient<GooglePlacesClient>()
                    .ConfigureHttpClient(client =>
                    {
                        client.Timeout = TimeSpan.FromSeconds(10); // Quick autocomplete timeout
                    })
                    .AddPolicyHandler(GetRetryPolicy());

                return services;
            }
        }

        // Retrieve Google Places configuration from AWS Secrets Manager (Production)
        try
        {
            var secretId = configuration["AWS:GooglePlacesSecretId"] ?? "receiptly/google/credentials";
            var region = configuration["AWS:Region"] ?? "ap-southeast-1";

            Log.Information("Retrieving Google Places configuration from Secrets Manager: {SecretId}", secretId);

            using var secretsClient = new AmazonSecretsManagerClient(Amazon.RegionEndpoint.GetBySystemName(region));
            var secretResponse = await secretsClient.GetSecretValueAsync(new GetSecretValueRequest
            {
                SecretId = secretId
            });

            googleConfig = JsonSerializer.Deserialize<GooglePlacesSecretsConfig>(secretResponse.SecretString)
                ?? throw new InvalidOperationException("Failed to deserialize Google Places configuration from Secrets Manager");

            Log.Information("Successfully retrieved Google Places configuration");
        }
        catch (Exception ex)
        {
            Log.Warning(ex, "Failed to retrieve Google Places configuration from Secrets Manager. Service will be disabled.");

            // Disable service if credentials not available
            googleConfig = new GooglePlacesSecretsConfig
            {
                ApiKey = string.Empty,
                Enabled = false
            };
        }

        services.AddSingleton(googleConfig);
        services.AddHttpClient<GooglePlacesClient>()
            .ConfigureHttpClient(client =>
            {
                client.Timeout = TimeSpan.FromSeconds(10); // Quick autocomplete timeout
            })
            .AddPolicyHandler(GetRetryPolicy());

        return services;
    }

    private static IAsyncPolicy<HttpResponseMessage> GetRetryPolicy()
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
                        "Retry {RetryCount}/3. Waiting {Delay}s before next attempt. Reason: {Reason}",
                        retryCount,
                        timespan.TotalSeconds,
                        outcome.Exception?.Message ?? outcome.Result?.StatusCode.ToString() ?? "Unknown");
                });
    }
}
