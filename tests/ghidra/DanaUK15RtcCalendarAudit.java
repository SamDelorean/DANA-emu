// @category Dana
// Inspect original ROM calendar hardware callsites; no firmware alteration.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.Memory;
import java.io.*;
public class DanaUK15RtcCalendarAudit extends GhidraScript {
 public void run() throws Exception {
  PrintWriter out=new PrintWriter(new FileWriter(getScriptArgs()[0]));
  Memory mem=currentProgram.getMemory();
  byte[] a=new byte[0x5d0000];
  int got=mem.getBytes(toAddr(0x10000000),a);
  out.printf("BASE 10000000 BYTES %d\n",got);
  long[] regs={0xfffffb00L,0xfffffb02L,0xfffffb1aL,0xfffffb1cL,0xfffffb0cL};
  for(long key:regs){
   int hits=0;
   for(int p=0;p<got-3;p+=2){
    long value=((long)(a[p]&255)<<24)|((a[p+1]&255)<<16)|((a[p+2]&255)<<8)|(a[p+3]&255);
    if (value==key){
     hits++;
     out.printf("REF %08X near=%08X ",key,p+0x10000000L);
     for(int k=Math.max(0,p-12);k<Math.min(got,p+12);k++)out.printf("%02X",a[k]&255);
     out.println();
     long inspos=0x10000000L+p-4;
     for(int j=0;j<5;j++){
      Instruction ins=getInstructionAt(toAddr(inspos));
      if(ins==null){try{disassemble(toAddr(inspos));}catch(Exception e){} ins=getInstructionAt(toAddr(inspos));}
      if(ins!=null) {out.printf("  %08X %s\n",inspos,ins.toString());inspos+=ins.getLength();}
      else inspos+=2;
     }
    }
   }
   out.printf("TOTAL %08X %d\n",key,hits);
  }
  out.close();
 }
}
