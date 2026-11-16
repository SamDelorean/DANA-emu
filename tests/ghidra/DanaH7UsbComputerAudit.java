// license:BSD-3-Clause
// @category Dana
// Read-only bounded audit of original UK1.5 USB Computer paths.
// Requires the EXISTING private Ghidra Dana project on T; does not import or patch ROM.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import java.io.File;
import java.io.PrintWriter;

public class DanaH7UsbComputerAudit extends GhidraScript {
    // Observed entrypoints from docs/ISP1161_USB_INTEGRATION_20261030.md.
    // A firmware occurrence/call graph is NOT proof of a physical PCB net.
    private static final long[] SITES = {
        0x1007CEF6L, // HwrIRQ2 entry
        0x10081732L, 0x10081736L, 0x10081740L, 0x10081748L, // C0 low/high
        0x100819E6L, 0x10081A7AL, 0x10081BE0L, // endpoint/connect/PG3
        0x100824FAL, 0x10082964L, 0x10082AA0L, // SETUP, IN, OUT
        0x102DD74EL, 0x102DE0A4L, 0x102DE138L,
        0x102DEFFAL, 0x102DF2A2L, 0x102DF362L,
        0x102DFAB8L, 0x102DFD86L
    };
    public void run() throws Exception {
        String[] args=getScriptArgs();
        if(args.length!=1)throw new IllegalArgumentException("Usage: script <output-path>");
        File target=new File(args[0]);
        if(target.exists())throw new IllegalArgumentException("Refuse to overwrite existing evidence: "+target);
        if(currentProgram==null)throw new IllegalStateException("No current UK1.5 program");
        try(PrintWriter out=new PrintWriter(target,"UTF-8")) {
            out.println("DANA H7 USB COMPUTER — READONLY NATIVE ROM AUDIT");
            out.println("Language="+currentProgram.getLanguageID()+" Program="+currentProgram.getName());
            out.println("No disassembly, decompilation, memory mapping or program mutation performed");
            for(long site:SITES) {
                Address address=toAddr(site);
                out.printf("%n=== SITE %08X ===%n",site);
                Function fn=currentProgram.getFunctionManager().getFunctionContaining(address);
                out.println("CONTAINING_FUNCTION="+(fn==null?"UNKNOWN":fn.getEntryPoint()+" "+fn.getName()));
                Instruction at=currentProgram.getListing().getInstructionContaining(address);
                out.println("INSTRUCTION_AT_SITE="+(at==null?"NOT_DISASSEMBLED":at.getAddress()+" "+at));
                for(Reference ref:currentProgram.getReferenceManager().getReferencesTo(address))
                    out.println("INCOMING_REF="+ref.getFromAddress()+" "+ref.getReferenceType());
                Address start=address.subtract(0x20),end=address.add(0x40);
                InstructionIterator it=currentProgram.getListing().getInstructions(new AddressSet(start,end),true);
                int budget=0;
                while(it.hasNext()&&budget++<55) {
                    Instruction ins=it.next();
                    out.println("TRACE="+ins.getAddress()+" "+ins);
                }
            }
            out.println("EVIDENCE_BOUNDARY: source instructions only; no guest run/SoftConnect/USB enumeration/physical continuity proven");
            out.println("NEXT: correlate HwrIRQ2, DC B8/B9, BA/BB, SETUP dispatch, PG3 with real guest MMIO trace");
        }
        println("H7_USB_READONLY_AUDIT_DONE sites="+SITES.length);
    }
}
