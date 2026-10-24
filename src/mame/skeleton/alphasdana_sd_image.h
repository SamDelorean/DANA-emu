// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors
#ifndef MAME_SKELETON_ALPHASDANA_SD_IMAGE_H
#define MAME_SKELETON_ALPHASDANA_SD_IMAGE_H

#include "alphasdana_sd.h"

// MAME image selection, per-slot mount/eject and config persistence; no host
// filesystem interpretation, hidden image creation, CHS rounding or writes.
class dana_sd_image_device;
DECLARE_DEVICE_TYPE(DANA_SD_IMAGE, dana_sd_image_device)
class dana_sd_image_device : public device_t, public device_image_interface
{
public:
    dana_sd_image_device(const machine_config &config,const char *tag,device_t *owner,u32 clock=0)
        : device_t(config,DANA_SD_IMAGE,tag,owner,clock), device_image_interface(config,*this) {}
    bool present() const { return exists(); }
    bool selected() const { return m_card.powered && m_card.selected && exists(); }
    bool read_sector(u32 lba,u8 *data)
    {
        return exists() && u64(lba)*512+512<=length() && !fseek(u64(lba)*512,SEEK_SET) && fread(data,512)==512;
    }
    void lines(bool power,bool select) { m_card.power(power); m_card.select(select && power); }
    bool bit(bool mosi) { return m_card.bit(mosi,*this); }
    virtual bool is_readable() const noexcept override { return true; }
    virtual bool is_writeable() const noexcept override { return false; }
    virtual bool is_creatable() const noexcept override { return false; }
    virtual bool is_reset_on_load() const noexcept override { return false; }
    virtual const char *file_extensions() const noexcept override { return "img,ima,bin,raw,sd"; }
    virtual const char *image_type_name() const noexcept override { return "sdcard"; }
    virtual const char *image_brief_type_name() const noexcept override { return "sd"; }
    virtual const char *image_interface() const noexcept override { return "dana_sd_raw"; }
protected:
    virtual void device_start() override
    {
#define DANA_SD_SAVE(member) save_item(NAME(m_card.member))
        DANA_SD_SAVE(cmd); DANA_SD_SAVE(reply); DANA_SD_SAVE(reply_pos); DANA_SD_SAVE(reply_size);
        DANA_SD_SAVE(write_left); DANA_SD_SAVE(command_size); DANA_SD_SAVE(bit_count);
        DANA_SD_SAVE(input); DANA_SD_SAVE(output); DANA_SD_SAVE(initial_clocks);
        DANA_SD_SAVE(status); DANA_SD_SAVE(blocks); DANA_SD_SAVE(next_block);
        DANA_SD_SAVE(powered); DANA_SD_SAVE(selected); DANA_SD_SAVE(idle); DANA_SD_SAVE(app);
        DANA_SD_SAVE(crc_enabled); DANA_SD_SAVE(high_capacity); DANA_SD_SAVE(multi_read); DANA_SD_SAVE(multi_write);
#undef DANA_SD_SAVE
        save_item(NAME(m_bound)); save_item(NAME(m_sha1));
        machine().save().register_presave(save_prepost_delegate(FUNC(dana_sd_image_device::check_media),this));
        machine().save().register_postload(save_prepost_delegate(FUNC(dana_sd_image_device::check_media),this));
    }
    virtual std::pair<std::error_condition,std::string> call_load() override
    {
        bool hc=false; u8 mult=0; u16 size=0;
        u64 const bytes=length();
        if (loaded_through_softlist() || bytes%512 || bytes/512>0x4000000
            || !dana_sd::card::geometry(u32(bytes/512),hc,mult,size))
            return {image_error::INVALIDLENGTH,"Raw 512-byte-sector image with exactly representable SD/SDHC capacity required (maximum 32 GiB)"};
        u8 signature[8];
        if (fseek(0,SEEK_SET) || fread(signature,8)!=8 || !std::memcmp(signature,"MComprHD",8) || !std::memcmp(signature,"DANARAM1",8))
            return {image_error::INVALIDIMAGE,"Select a raw SD sector image, not CHD, firmware or a RAM guest"};
        // Read the whole original with bounded memory; do not trust filename,
        // timestamps or the first sector as saved-state media identity.
        if (!fingerprint(m_sha1))
            return {image_error::INVALIDIMAGE,"Short or failed SD image read"};
        m_bound=true;
        bool const power=m_card.powered, selected=m_card.selected;
        m_card=dana_sd::card{}; m_card.blocks=bytes/512;
        m_card.power(power); m_card.select(selected);
        logerror("DANA_SD_MOUNT slot=%s bytes=%llu read_only=1\n",tag(),(unsigned long long)bytes);
        return {};
    }
    virtual void call_unload() override
    {
        // No writeback exists. Discard partial SPI/data frames on eject and
        // keep the other slot, GPIO power and shared SPI controller intact.
        bool const power=m_card.powered, selected=m_card.selected;
        m_card=dana_sd::card{}; m_card.power(power); m_card.select(selected);
        m_bound=false; std::fill(std::begin(m_sha1),std::end(m_sha1),0);
        logerror("DANA_SD_EJECT slot=%s\n",tag());
    }
private:
    bool fingerprint(u8 *result)
    {
        util::sha1_creator hash;
        std::array<u8,65536> chunk;
        u64 remaining=length();
        if (fseek(0,SEEK_SET)) return false;
        while (remaining)
        {
            u32 const count=u32(std::min<u64>(remaining,chunk.size()));
            if (fread(chunk.data(),count)!=count) return false;
            hash.append(chunk.data(),count); remaining-=count;
        }
        auto const value=hash.finish();
        std::copy(std::begin(value.m_raw),std::end(value.m_raw),result);
        return true;
    }
    void check_media()
    {
        if (m_bound!=exists()) fatalerror("SD slot %s presence differs from saved media selection",tag());
        if (!m_bound) return;
        u8 actual[20];
        if (u64(m_card.blocks)*512!=length() || !fingerprint(actual) || std::memcmp(actual,m_sha1,20))
            fatalerror("SD slot %s image changed; refuse stale or mismatched saved state",tag());
    }
    dana_sd::card m_card;
    bool m_bound=false;
    u8 m_sha1[20]={};
};
DEFINE_DEVICE_TYPE(DANA_SD_IMAGE,dana_sd_image_device,"dana_sd_image","Dana read-only raw SD card")
#endif
