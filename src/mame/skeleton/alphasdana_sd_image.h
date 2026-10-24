// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors
#ifndef MAME_SKELETON_ALPHASDANA_SD_IMAGE_H
#define MAME_SKELETON_ALPHASDANA_SD_IMAGE_H

#include "alphasdana_sd.h"

// MAME image selection, per-slot mount/eject and config persistence; no host
// filesystem interpretation, hidden image creation or CHS rounding. Each
// existing file is writable only through that slot's explicit SDWRITE switch.
class dana_sd_image_device;
DECLARE_DEVICE_TYPE(DANA_SD_IMAGE, dana_sd_image_device)
class dana_sd_image_device : public device_t, public device_image_interface
{
public:
    dana_sd_image_device(const machine_config &config,const char *tag,device_t *owner,u32 clock=0)
        : device_t(config,DANA_SD_IMAGE,tag,owner,clock), device_image_interface(config,*this), m_write_access(*this,"^SDWRITE") {}
    void set_slot(unsigned slot) { m_slot=slot; }
    bool write_protected() const
    { return !exists() || is_readonly() || m_io_fault || !(m_write_access->read() & (1U<<m_slot)); }
    bool present() const { return exists(); }
    bool selected() const { return m_card.powered && m_card.selected && exists(); }
    bool read_sector(u32 lba,u8 *data)
    {
        return exists() && !m_io_fault && u64(lba)*512+512<=length() && !fseek(u64(lba)*512,SEEK_SET) && fread(data,512)==512;
    }
    bool write_sector(u32 lba,const u8 *data)
    {
        if (write_protected() || !m_bound || u64(lba)*512+512>length()) return false;
        u8 before[20],expected[20];
        if (!fingerprint(before,lba,data,expected) || std::memcmp(before,m_sha1,20))
            return fail_write("MEDIA_CHANGED_BEFORE_WRITE",lba);
        // Unlike device_image_interface::fwrite, the util API retains both
        // the error and exact byte count. Never extend/create/replace a file.
        auto const [error,actual]=util::write_at(image_core_file(),u64(lba)*512,data,512);
        if (error || actual!=512) return fail_write("BACKEND_WRITE_OR_SHORT_WRITE",lba);
        if (image_core_file().flush()) return fail_write("BACKEND_FLUSH",lba);
        u8 verified[512],after[20];
        auto const [read_error,read_actual]=util::read_at(image_core_file(),u64(lba)*512,verified,512);
        if (read_error || read_actual!=512 || std::memcmp(verified,data,512))
            return fail_write("BACKEND_READBACK",lba);
        if (!fingerprint(after) || std::memcmp(after,expected,20))
            return fail_write("MEDIA_CHANGED_DURING_WRITE",lba);
        std::copy(std::begin(after),std::end(after),std::begin(m_sha1));
        ++m_committed_blocks;
        logerror("DANA_SD_WRITE slot=%s lba=%u bytes=512 committed=%u flush=backend power_loss_durable=unqualified\n",tag(),lba,m_committed_blocks);
        return true;
    }
    void lines(bool power,bool select) { m_card.power(power); m_card.select(select && power); }
    bool bit(bool mosi) { return m_card.bit(mosi,*this); }
    virtual bool is_readable() const noexcept override { return true; }
    virtual bool is_writeable() const noexcept override { return true; }
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
        DANA_SD_SAVE(cmd); DANA_SD_SAVE(reply); DANA_SD_SAVE(write_data); DANA_SD_SAVE(write_reply); DANA_SD_SAVE(reply_pos); DANA_SD_SAVE(reply_size);
        DANA_SD_SAVE(write_left); DANA_SD_SAVE(command_size); DANA_SD_SAVE(bit_count);
        DANA_SD_SAVE(input); DANA_SD_SAVE(output); DANA_SD_SAVE(initial_clocks);
        DANA_SD_SAVE(status); DANA_SD_SAVE(blocks); DANA_SD_SAVE(next_block);
        DANA_SD_SAVE(powered); DANA_SD_SAVE(selected); DANA_SD_SAVE(idle); DANA_SD_SAVE(app);
        DANA_SD_SAVE(crc_enabled); DANA_SD_SAVE(high_capacity); DANA_SD_SAVE(multi_read); DANA_SD_SAVE(multi_write);
#undef DANA_SD_SAVE
        save_item(NAME(m_bound)); save_item(NAME(m_sha1));
        save_item(NAME(m_saved_writable)); save_item(NAME(m_committed_blocks));
        // m_io_fault is live session quarantine, never cleared by state restore.
        machine().save().register_presave(save_prepost_delegate(FUNC(dana_sd_image_device::before_save),this));
        machine().save().register_postload(save_prepost_delegate(FUNC(dana_sd_image_device::after_load),this));
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
        m_bound=true; m_io_fault=false; m_committed_blocks=0;
        bool const power=m_card.powered, selected=m_card.selected;
        m_card=dana_sd::card{}; m_card.blocks=bytes/512;
        m_card.power(power); m_card.select(selected);
        // Image loading occurs before input ports are initialized: never read SDWRITE here.
        // The effective per-slot write permission is evaluated only at runtime.
        logerror("DANA_SD_MOUNT slot=%s bytes=%llu backend_read_only=%u policy=runtime\n",tag(),(unsigned long long)bytes,unsigned(is_readonly()));
        return {};
    }
    virtual void call_unload() override
    {
        // Complete blocks were already written/flushed/verified synchronously.
        // Never commit a partial frame on eject, reset, power-off or close.
        // Keep the other slot and shared SPI controller intact.
        if (is_open() && !is_readonly() && image_core_file().flush())
            logerror("DANA_SD_EJECT_FLUSH_ERROR slot=%s\n",tag());
        bool const power=m_card.powered, selected=m_card.selected;
        m_card=dana_sd::card{}; m_card.power(power); m_card.select(selected);
        m_bound=false; m_io_fault=false; std::fill(std::begin(m_sha1),std::end(m_sha1),0);
        logerror("DANA_SD_EJECT slot=%s\n",tag());
    }
private:
    bool fail_write(const char *reason,u32 lba)
    {
        // A failed in-place write might have changed part of a sector. Do not
        // bless its new hash or continue I/O; preserve the file for diagnosis.
        m_io_fault=true;
        logerror("DANA_SD_WRITE_ERROR slot=%s lba=%u reason=%s quarantine=1\n",tag(),lba,reason);
        return false;
    }
    bool fingerprint(u8 *result,u32 replacement_lba=~u32(0),const u8 *replacement=nullptr,u8 *predicted=nullptr)
    {
        util::sha1_creator hash,changed;
        std::array<u8,65536> chunk;
        u64 remaining=length(),position=0;
        if (fseek(0,SEEK_SET)) return false;
        while (remaining)
        {
            u32 const count=u32(std::min<u64>(remaining,chunk.size()));
            if (fread(chunk.data(),count)!=count) return false;
            hash.append(chunk.data(),count);
            if (predicted)
            {
                u64 const offset=u64(replacement_lba)*512;
                if (replacement && offset>=position && offset+512<=position+count)
                    std::copy_n(replacement,512,chunk.data()+(offset-position));
                changed.append(chunk.data(),count);
            }
            remaining-=count; position+=count;
        }
        auto const value=hash.finish();
        std::copy(std::begin(value.m_raw),std::end(value.m_raw),result);
        if (predicted)
        {
            auto const modified=changed.finish();
            std::copy(std::begin(modified.m_raw),std::end(modified.m_raw),predicted);
        }
        return true;
    }
    void before_save()
    {
        check_media();
        m_saved_writable=m_bound && !write_protected();
    }
    void after_load()
    {
        // Configuration is saved by MAME separately. A state must never
        // silently enable writes or replay a completed block against old media.
        check_media();
        if (m_saved_writable!=(m_bound && !write_protected()))
            fatalerror("SD slot %s write protection differs from saved state",tag());
    }
    void check_media()
    {
        if (m_bound!=exists()) fatalerror("SD slot %s presence differs from saved media selection",tag());
        if (m_io_fault) fatalerror("SD slot %s has an unresolved backend fault; remount verified media before saving/restoring",tag());
        if (!m_bound) return;
        u8 actual[20];
        if (u64(m_card.blocks)*512!=length() || !fingerprint(actual) || std::memcmp(actual,m_sha1,20))
            fatalerror("SD slot %s image changed; refuse stale or mismatched saved state",tag());
    }
    required_ioport m_write_access;
    unsigned m_slot=0;
    bool m_saved_writable=false,m_io_fault=false;
    u32 m_committed_blocks=0;
    dana_sd::card m_card;
    bool m_bound=false;
    u8 m_sha1[20]={};
};
DEFINE_DEVICE_TYPE(DANA_SD_IMAGE,dana_sd_image_device,"dana_sd_image","Dana raw SD card (write protected by default)")
#endif
