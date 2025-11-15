using Receiptly.API.Configuration;
using Serilog;

// Configure Serilog
SerilogConfiguration.ConfigureLogger();

try
{
    Log.Information("Starting Receiptly API");

    var builder = WebApplication.CreateBuilder(args);

    // Add Serilog
    builder.Host.UseSerilog();

    // Configure CORS policies
    builder.Services.AddCorsConfiguration(builder.Configuration);

    // Configure Controllers with JSON options
    builder.Services.AddControllers()
        .AddJsonOptions(options =>
        {
            // Prevent circular reference errors when serializing Receipt <-> Items
            options.JsonSerializerOptions.ReferenceHandler = System.Text.Json.Serialization.ReferenceHandler.IgnoreCycles;
            options.JsonSerializerOptions.DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull;
        });

    // Configure Database (with AWS Secrets Manager)
    await builder.Services.AddDatabaseConfiguration(builder.Configuration, builder.Environment);

    // Configure AWS Services (S3)
    await builder.Services.AddAwsServices(builder.Configuration);

    // Configure OCR Service
    await builder.Services.AddOcrService(builder.Configuration);

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
    Log.Fatal(ex, "Application terminated unexpectedly");
}
finally
{
    Log.CloseAndFlush();
}
