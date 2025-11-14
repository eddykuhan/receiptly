using AutoMapper;
using Receiptly.API.DTOs;
using Receiptly.Domain.Models;

namespace Receiptly.API.Mappings;

/// <summary>
/// AutoMapper profile for mapping between domain models and DTOs
/// </summary>
public class MappingProfile : Profile
{
    public MappingProfile()
    {
        // Receipt -> ReceiptDto
        CreateMap<Receipt, ReceiptDto>()
            .ForMember(dest => dest.Items, opt => opt.MapFrom(src => src.Items));
        
        // Item -> ItemDto (exclude Receipt to prevent circular reference)
        CreateMap<Item, ItemDto>();
    }
}
