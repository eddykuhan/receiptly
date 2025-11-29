using Receiptly.API.Configuration;
using Serilog;

// Configure Serilog
SerilogConfiguration.ConfigureLogger();

try
{
    Log.Information("Starting Receiptly API");

    var builder = WebApplication.CreateBuilder(args);

    // Configure Kestrel for mobile uploads (large files, longer processing time)
    builder.WebHost.ConfigureKestrel(options =>
    {
        options.Limits.MaxRequestBodySize = 15 * 1024 * 1024; // 15MB (mobile images can be large)
        options.Limits.RequestHeadersTimeout = TimeSpan.FromMinutes(5); // 5 minutes
        options.Limits.KeepAliveTimeout = TimeSpan.FromMinutes(5);
    });

    // Add Serilog
    builder.Host.UseSerilog();

    // Configure CORS policies
    builder.Services.AddCorsConfiguration(builder.Configuration);

    // Configure form options for file uploads
    builder.Services.Configure<Microsoft.AspNetCore.Http.Features.FormOptions>(options =>
    {
        options.MultipartBodyLengthLimit = 15 * 1024 * 1024; // 15MB
        options.ValueLengthLimit = 15 * 1024 * 1024;
        options.BufferBodyLengthLimit = 15 * 1024 * 1024;
    });

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
    await builder.Services.AddOcrService(builder.Configuration, builder.Environment);

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
