using Receiptly.API.Configuration;

var builder = WebApplication.CreateBuilder(args);

try
{

    // Configure Kestrel for mobile uploads (large files, longer processing time)
    builder.WebHost.ConfigureKestrel(options =>
    {
        options.Limits.MaxRequestBodySize = 15 * 1024 * 1024; // 15MB (mobile images can be large)
        options.Limits.RequestHeadersTimeout = TimeSpan.FromMinutes(5); // 5 minutes
        options.Limits.KeepAliveTimeout = TimeSpan.FromMinutes(5);
    });

    // Configure CORS policies
    builder.Services.AddCorsConfiguration(builder.Configuration);

    // Configure form options for file uploads
    builder.Services.Configure<Microsoft.AspNetCore.Http.Features.FormOptions>(options =>
    {
        options.MultipartBodyLengthLimit = 15 * 1024 * 1024; // 15MB
        options.ValueLengthLimit = 15 * 1024 * 1024;
        options.BufferBodyLengthLimit = 15 * 1024 * 1024;
    });

    // Configure OpenTelemetry (Tracing, Metrics & Logging)
    builder.Services.AddOpenTelemetryConfiguration(builder.Configuration, builder.Environment);

    // Add HTTP logging for request/response logging
    builder.Services.AddHttpLogging(logging =>
    {
        logging.LoggingFields = Microsoft.AspNetCore.HttpLogging.HttpLoggingFields.All;
    });

    // Configure Controllers with JSON options
    builder.Services.AddControllers()
        .AddJsonOptions(options =>
        {
            // Prevent circular reference errors when serializing Receipt <-> Items
            options.JsonSerializerOptions.ReferenceHandler = System.Text.Json.Serialization.ReferenceHandler.IgnoreCycles;
            options.JsonSerializerOptions.DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull;
            // Use camelCase for JSON property names to match JavaScript conventions
            options.JsonSerializerOptions.PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.CamelCase;
        });

    // Configure Database (with AWS Secrets Manager)
    await builder.Services.AddDatabaseConfiguration(builder.Configuration, builder.Environment);

    // Configure AWS Services (S3)
    await builder.Services.AddAwsServices(builder.Configuration);

    // Configure OCR Service
    await builder.Services.AddOcrService(builder.Configuration, builder.Environment);

    // Configure LLM Service
    await builder.Services.AddLlmService(builder.Configuration, builder.Environment);

    // Configure Google Places Service
    await builder.Services.AddGooglePlacesService(builder.Configuration, builder.Environment);

    // Add Application Services
    builder.Services.AddApplicationServices();

    // Configure Swagger/OpenAPI
    builder.Services.AddEndpointsApiExplorer();
    builder.Services.AddSwaggerGen();

    var app = builder.Build();

    // Apply database migrations (development only)
    await app.ApplyDatabaseMigrations();

    // Configure middleware pipeline
    app.ConfigureMiddleware();

    // Map endpoints
    app.MapEndpoints();

    app.Run();
}
catch (Exception ex)
{
    Console.WriteLine($"Application terminated unexpectedly: {ex}");
    throw;
}
